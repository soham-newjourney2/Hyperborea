"""P05 endpoints: /weather/current, /weather/forecast, /climate/summary, /scenarios/presets (planning §8)."""
import json

import yaml
from fastapi import APIRouter, HTTPException

from ..core.paths import CONFIG
from ..core.regions import data_dir, per_region
from ..services.layer_store import get_store
from ..services.weather import WeatherUnavailable, get_weather

router = APIRouter()


def _weather() -> dict:
    region = get_store().region()
    if region is None:
        raise HTTPException(503, "No region loaded")
    lon, lat = region["centroid"]
    try:
        return get_weather(lat, lon)
    except WeatherUnavailable as e:
        raise HTTPException(503, str(e)) from e


@router.get("/weather/current")
def weather_current() -> dict:
    w = _weather()
    w.pop("hourly")
    return w


@router.get("/weather/forecast")
def weather_forecast() -> dict:
    return _weather()


@per_region
def climate_summary_data() -> dict | None:
    path = data_dir() / "climate_summary.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


@router.get("/climate/summary")
def climate_summary() -> dict:
    s = climate_summary_data()
    if s is None:
        raise HTTPException(503, "Climate summary missing — run pipelines.climate")
    return s


@per_region
def presets_data() -> list[dict]:
    cfg = yaml.safe_load((CONFIG / "scenarios.yaml").read_text(encoding="utf-8"))
    climate = climate_summary_data()
    out = []
    for p in cfg["presets"]:
        p = {**p, "data_status": "simulated", "source_id": "syn_rain"}
        p["total_mm"] = round(p.get("rain_mm_h", 0) * p["duration_h"], 1)
        if p.pop("from_climate", None) == "max_1day":
            if climate is None:
                continue
            m = climate["stats"]["max_1day"]
            p["rain_mm_h"] = round(m["mm"] / p["duration_h"], 1)
            p["total_mm"] = m["mm"]  # exact ERA5 total; rain_mm_h is the rounded uniform rate
            p["description"] += f" ({m['mm']} mm on {m['date']})"
            p["source_id"] = "om_archive"
        out.append(p)
    return out


@router.get("/scenarios/presets")
def scenario_presets() -> list[dict]:
    return presets_data()
