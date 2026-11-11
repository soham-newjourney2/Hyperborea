"""P21: GET /warning — 72 h forecast → flood-cascade outlook for the active region (cached per forecast fetch)."""
from datetime import datetime, timezone

import yaml
from fastapi import APIRouter, HTTPException

from ...engine import surrogate as sg
from ...engine import warning as ew
from ..core.paths import CONFIG
from ..core.regions import current
from .scenarios import attach_access, flood_context, result_cache
from .weather import _weather

router = APIRouter()
_cache: dict[tuple[str, str], dict] = {}


def rules() -> dict:
    return yaml.safe_load((CONFIG / "warning.yaml").read_text(encoding="utf-8"))


DEMO_BURST = [5.0, 25.0, 45.0, 38.0, 12.0, 3.0]  # mm/h, starting 18 h from the forecast start — synthetic


def _demo(w: dict) -> dict:
    """Same forecast hours, rain replaced by a synthetic convective burst (clearly labelled; for demos when it is dry)."""
    hourly = [{**h, "precipitation": 0.0, "precipitation_probability": 0} for h in w["hourly"]]
    for i, r in enumerate(DEMO_BURST):
        if 18 + i < len(hourly):
            hourly[18 + i].update(precipitation=r, precipitation_probability=70)
    return {**w, "hourly": hourly, "fetched_at": w["fetched_at"] + "#demo"}


@router.get("/warning")
def warning(demo: bool = False) -> dict:
    w = _demo(_weather()) if demo else _weather()
    key = (current(), w["fetched_at"])
    if key in _cache:
        return _cache[key]
    ctx = flood_context()
    if sg.load_model() is None:
        raise HTTPException(503, "Surrogate model missing — run pipelines.train_surrogate")

    def quick(rain: float, dur: float) -> int:
        return sg.quickscan(ctx, rain, dur, 1.0)["predicted_overloads"]

    def run(rain: float, dur: float) -> dict:
        params = {"preset": None, "preset_source_id": "syn_rain" if demo else "om_forecast", "rain_mm_h": round(rain, 2),
                  "duration_h": round(dur, 2), "condition_scale": 1.0}
        return attach_access(result_cache().get_or_run(ctx, params))

    out = ew.outlook(w["hourly"], quick, run, rules())
    if demo:
        out.update(demo=True, data_status="simulated", source_ids=["syn_rain", "ml_surrogate", "syn_drain"],
                   label="DEMO — synthetic rain burst replacing the forecast (not real weather); " + ew.LABEL,
                   headline="DEMO · " + out["headline"])
    out.update(region=current(), forecast_fetched_at=w["fetched_at"], forecast_stale=w.get("stale", False),
               generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    _cache[key] = out
    if len(_cache) > 20:
        _cache.pop(next(iter(_cache)))
    return out
