"""P05: Open-Meteo forecast for the pilot (modelled), cached 30 min, stale fallback to last cache / snapshot."""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import httpx

from ..core.paths import LOCAL, SNAPSHOTS

URL = "https://api.open-meteo.com/v1/forecast"
CURRENT = "temperature_2m,relative_humidity_2m,precipitation,rain,wind_speed_10m,weather_code"
HOURLY = "precipitation,rain,temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation_probability"
TTL_S = 30 * 60
CACHE = LOCAL / "cache" / "weather.json"
SNAPSHOT = SNAPSHOTS / "weather.json"
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"

# WMO weather interpretation codes (Open-Meteo docs), condensed.
WMO = {0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Rime fog",
       51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
       80: "Light showers", 81: "Showers", 82: "Violent showers", 95: "Thunderstorm",
       96: "Thunderstorm, hail", 99: "Thunderstorm, heavy hail"}


class WeatherUnavailable(RuntimeError):
    pass


def fetch_live(lat: float, lon: float) -> dict:
    params = {"latitude": lat, "longitude": lon, "current": CURRENT, "hourly": HOURLY, "forecast_hours": 72,
              "timezone": "Asia/Kolkata"}
    r = httpx.get(URL, params=params, timeout=5, headers={"User-Agent": "Hyperborea/0.1"})
    r.raise_for_status()
    return r.json()


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _wrap(entry: dict, *, stale: bool, origin: str, reason: str | None = None) -> dict:
    raw = entry["raw"]
    cur = dict(raw.get("current", {}))
    cur["condition"] = WMO.get(cur.get("weather_code"), "—")
    h = raw.get("hourly", {})
    hourly = [dict(zip(h.keys(), vals)) for vals in zip(*h.values())] if h else []
    return {
        "source_id": "om_forecast", "data_status": "modelled", "attribution": ATTRIBUTION,
        "fetched_at": entry["fetched_at"], "stale": stale, "origin": origin, "stale_reason": reason,
        "location": {"lat": raw.get("latitude"), "lon": raw.get("longitude"), "elevation_m": raw.get("elevation"),
                     "timezone": raw.get("timezone")},
        "units": {**raw.get("current_units", {}), **raw.get("hourly_units", {})},
        "current": cur, "hourly": hourly,
    }


def get_weather(lat: float, lon: float, fetch: Callable[[float, float], dict] = fetch_live,
                cache: Path = CACHE, snapshot: Path = SNAPSHOT) -> dict:
    cached = _read(cache)
    if cached and time.time() - cached.get("fetched_ts", 0) < TTL_S:
        return _wrap(cached, stale=False, origin="cache")
    try:
        raw = fetch(lat, lon)
    except Exception as e:  # noqa: BLE001 — any network/HTTP/parse failure → stale fallback
        reason = f"Open-Meteo unavailable ({type(e).__name__})"
        for origin, entry in (("cache", cached), ("snapshot", _read(snapshot))):
            if entry:
                return _wrap(entry, stale=True, origin=origin, reason=reason)
        raise WeatherUnavailable(reason) from e
    entry = {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "fetched_ts": time.time(),
             "raw": raw}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(entry), encoding="utf-8")
    return _wrap(entry, stale=False, origin="live")
