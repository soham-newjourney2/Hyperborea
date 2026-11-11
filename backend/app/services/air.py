"""P11: Open-Meteo Air Quality (CAMS, modelled) for the pilot centroid → 24 h means → India NAQI (CPCB 2014).

Same caching/fallback pattern as weather.py: 60 min cache in local/cache, stale fallback to cache / snapshot.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from functools import lru_cache
from pathlib import Path

import httpx
import yaml

from ..core.paths import CONFIG, LOCAL, SNAPSHOTS
from ..core.regions import cfg, data_dir, local_dir

URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
POLLUTANTS = ["pm2_5", "pm10", "nitrogen_dioxide", "ozone"]
TTL_S = 60 * 60
CACHE = LOCAL / "cache" / "air.json"
SNAPSHOT = SNAPSHOTS / "air.json"
ATTRIBUTION = "Air quality: CAMS (Copernicus Atmosphere Monitoring Service) via Open-Meteo.com (CC BY 4.0)"


class AirUnavailable(RuntimeError):
    pass


@lru_cache
def naqi_rules() -> dict:
    return yaml.safe_load((CONFIG / "naqi.yaml").read_text(encoding="utf-8"))


def sub_index(pollutant: str, conc: float) -> int:
    """CPCB linear interpolation within the breakpoint band: I = Ilo + (C − Clo)·(Ihi − Ilo)/(Chi − Clo)."""
    rules = naqi_rules()
    bps, cats = rules["breakpoints"][pollutant], rules["categories"]
    lo = 0.0
    for hi, cat in zip(bps, cats):
        if conc <= hi:
            ilo, ihi = cat["aqi"]
            return round(ilo + (conc - lo) * (ihi - ilo) / (hi - lo))
        lo = hi
    return 500


# Banded schemes (level = 1 + number of band lower bounds ≤ value; index = worst pollutant level)
BANDED = {
    "daqi": {"file": "daqi.yaml", "name": "DAQI", "scale": "1–10", "chart_max": 90,
             "stat": {"pm2_5": "mean24", "pm10": "mean24", "nitrogen_dioxide": "max1h", "ozone": "max8h"},
             "source": "Defra/COMEAP DAQI (GOV.UK, OGL v3)",
             "note": "DAQI computed from modelled CAMS concentrations (not Defra AURN station data); "
                     "PM 24-h mean, NO₂ max hourly, O₃ max 8-h mean of the last 24 h"},
    "nsw_aqc": {"file": "nsw_aqc.yaml", "name": "NSW AQC", "scale": "5 categories", "chart_max": 70,
                "stat": {"pm2_5": "mean24", "pm10": "mean24", "nitrogen_dioxide": "max1h", "ozone": "max1h"},
                "source": "NSW Air Quality Categories (NSW Government; O₃/NO₂ bands converted from pphm at 25 °C)",
                "note": "NSW air quality category computed from modelled CAMS concentrations (not NSW DCCEEW station "
                        "data); PM 24-h mean, O₃ and NO₂ worst hour of the last 24 h"},
}


@lru_cache
def banded_rules(scheme: str) -> dict:
    return yaml.safe_load((CONFIG / BANDED[scheme]["file"]).read_text(encoding="utf-8"))


def daqi_rules() -> dict:
    return banded_rules("daqi")


def banded_level(scheme: str, pollutant: str, conc: float) -> int:
    return 1 + sum(conc >= lo for lo in banded_rules(scheme)["lower"][pollutant])


def daqi_level(pollutant: str, conc: float) -> int:
    """UK DAQI level 1–10: 1 + number of band lower bounds ≤ concentration."""
    return banded_level("daqi", pollutant, conc)


def pm25_bands(scheme: str) -> list[list]:
    """[lo, hi, colour, label] PM2.5 bands for the chart, in the region's index scheme."""
    if scheme in BANDED:
        r = banded_rules(scheme)
        edges = [0, *r["lower"]["pm2_5"], BANDED[scheme]["chart_max"]]
        label = (lambda lv: f"{lv['level']} {lv['band']}") if scheme == "daqi" else (lambda lv: lv["band"])
        return [[edges[i], edges[i + 1], lv["color"], label(lv)] for i, lv in enumerate(r["levels"])]
    r = naqi_rules()
    edges = [0, *r["breakpoints"]["pm2_5"][:-1], 400]
    return [[edges[i], edges[i + 1], c["color"], c["name"]] for i, c in enumerate(r["categories"])]


def category(aqi: int) -> dict:
    for cat in naqi_rules()["categories"]:
        if aqi <= cat["aqi"][1]:
            return cat
    return naqi_rules()["categories"][-1]


def _stat(vals: list[float], how: str) -> float | None:
    if not vals:
        return None
    if how == "max1h":
        return round(max(vals), 1)
    if how == "max8h":
        runs = [sum(vals[i:i + 8]) / 8 for i in range(max(len(vals) - 7, 1))]
        return round(max(runs), 1)
    return round(sum(vals) / len(vals), 1)


def fetch_live(lat: float, lon: float) -> dict:
    params = {"latitude": lat, "longitude": lon, "hourly": ",".join(POLLUTANTS), "timezone": cfg()["timezone"],
              "past_days": 1, "forecast_days": 3}
    r = httpx.get(URL, params=params, timeout=5, headers={"User-Agent": "Hyperborea/0.1"})
    r.raise_for_status()
    return r.json()


def _read(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def summarise(raw: dict, now_local: str | None = None, scheme: str | None = None) -> dict:
    h = raw["hourly"]
    rows = [dict(zip(h.keys(), v)) for v in zip(*h.values())]
    scheme = scheme or cfg().get("aq_index", "naqi")
    tz = raw.get("timezone") or cfg()["timezone"]  # Open-Meteo returns times in the region timezone
    now_local = now_local or datetime.now(ZoneInfo(tz)).strftime("%Y-%m-%dT%H:00")
    past = [r for r in rows if r["time"] <= now_local][-24:] or rows[:24]
    means, subs = {}, {}
    naqi_stat = {"ozone": "max8h"}  # NAQI: O3 max 8-h, the rest 24-h means
    for p in POLLUTANTS:
        vals = [r[p] for r in past if r.get(p) is not None]
        how = BANDED[scheme]["stat"][p] if scheme in BANDED else naqi_stat.get(p, "mean24")
        means[p] = _stat(vals, how)
        if means[p] is None:
            subs[p] = None
        else:
            subs[p] = banded_level(scheme, p, means[p]) if scheme in BANDED else sub_index(p, means[p])
    valid = {k: v for k, v in subs.items() if v is not None}
    dom = max(valid, key=valid.get) if valid else None
    aqi = valid[dom] if dom else None
    if scheme in BANDED:
        meta = BANDED[scheme]
        lv = banded_rules(scheme)["levels"][aqi - 1] if aqi else None
        cat = {"name": (f"{lv['band']} ({aqi})" if scheme == "daqi" else lv["band"]), "color": lv["color"]} if lv else None
        index = {"id": scheme, "name": meta["name"], "scale": meta["scale"], "source": meta["source"]}
        note = meta["note"]
    else:
        cat = category(aqi) if aqi is not None else None
        index = {"id": "naqi", "name": "NAQI", "scale": "0–500", "source": "CPCB NAQI (2014)"}
        note = ("NAQI computed from modelled CAMS concentrations (not CPCB station data); "
                "PM/NO₂ 24-h mean, O₃ max 8-h mean of the last 24 h")
    return {"window": {"from": past[0]["time"], "to": past[-1]["time"], "hours": len(past)},
            "means_ugm3": means, "sub_index": subs, "aqi": aqi, "naqi": aqi if scheme == "naqi" else None,
            "index": index, "timezone": tz, "pm25_bands": pm25_bands(scheme), "dominant": dom,
            "category": cat["name"] if cat else None, "color": cat["color"] if cat else None,
            "note": note, "hourly": rows}


def get_air(lat: float, lon: float, fetch: Callable[[float, float], dict] = fetch_live, cache: Path | None = None,
            snapshot: Path | None = None) -> dict:
    cache = cache or local_dir("cache") / CACHE.name  # P16: one cache + snapshot per region
    snapshot = snapshot or data_dir("snapshots") / SNAPSHOT.name
    cached = _read(cache)
    origin, stale, reason = "cache", False, None
    if cached and time.time() - cached.get("fetched_ts", 0) < TTL_S:
        entry = cached
    else:
        try:
            entry = {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "fetched_ts": time.time(),
                     "raw": fetch(lat, lon)}
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(entry), encoding="utf-8")
            origin = "live"
        except Exception as e:  # noqa: BLE001 — any network/HTTP failure → stale fallback
            reason = f"Open-Meteo air quality unavailable ({type(e).__name__})"
            entry, origin = (cached, "cache") if cached else (_read(snapshot), "snapshot")
            stale = True
            if not entry:
                raise AirUnavailable(reason) from e
    raw = entry["raw"]
    return {"source_id": "om_aq", "data_status": "modelled", "attribution": ATTRIBUTION,
            "fetched_at": entry["fetched_at"], "stale": stale, "origin": origin, "stale_reason": reason,
            "location": {"lat": raw.get("latitude"), "lon": raw.get("longitude")},
            "units": raw.get("hourly_units", {}), **summarise(raw)}
