"""P11: Open-Meteo Air Quality (CAMS, modelled) for the pilot centroid → 24 h means → India NAQI (CPCB 2014).

Same caching/fallback pattern as weather.py: 60 min cache in local/cache, stale fallback to cache / snapshot.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import httpx
import yaml

from ..core.paths import CONFIG, LOCAL, SNAPSHOTS

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


def category(aqi: int) -> dict:
    for cat in naqi_rules()["categories"]:
        if aqi <= cat["aqi"][1]:
            return cat
    return naqi_rules()["categories"][-1]


def fetch_live(lat: float, lon: float) -> dict:
    params = {"latitude": lat, "longitude": lon, "hourly": ",".join(POLLUTANTS), "timezone": "Asia/Kolkata",
              "past_days": 1, "forecast_days": 3}
    r = httpx.get(URL, params=params, timeout=5, headers={"User-Agent": "Hyperborea/0.1"})
    r.raise_for_status()
    return r.json()


def _read(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def summarise(raw: dict, now_local: str | None = None) -> dict:
    h = raw["hourly"]
    rows = [dict(zip(h.keys(), v)) for v in zip(*h.values())]
    now_local = now_local or datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:00")
    past = [r for r in rows if r["time"] <= now_local][-24:] or rows[:24]
    means, subs = {}, {}
    for p in POLLUTANTS:
        vals = [r[p] for r in past if r.get(p) is not None]
        if p == "ozone":  # max 8-h running mean
            runs = [sum(vals[i:i + 8]) / 8 for i in range(max(len(vals) - 7, 1))] if vals else []
            means[p] = round(max(runs), 1) if runs else None
        else:
            means[p] = round(sum(vals) / len(vals), 1) if vals else None
        subs[p] = sub_index(p, means[p]) if means[p] is not None else None
    valid = {k: v for k, v in subs.items() if v is not None}
    dom = max(valid, key=valid.get) if valid else None
    aqi = valid[dom] if dom else None
    cat = category(aqi) if aqi is not None else None
    return {"window": {"from": past[0]["time"], "to": past[-1]["time"], "hours": len(past)},
            "means_ugm3": means, "sub_index": subs, "naqi": aqi, "dominant": dom,
            "category": cat["name"] if cat else None, "color": cat["color"] if cat else None,
            "note": "NAQI computed from modelled CAMS concentrations (not CPCB station data); "
                    "PM/NO₂ 24-h mean, O₃ max 8-h mean of the last 24 h",
            "hourly": rows}


def get_air(lat: float, lon: float, fetch: Callable[[float, float], dict] = fetch_live, cache: Path = CACHE,
            snapshot: Path = SNAPSHOT) -> dict:
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
