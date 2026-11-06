"""P08: POST /scenarios/flood (planning §8) — rainfall cascade on a scenario overlay."""
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...engine.flood import FloodContext, ResultCache, build_context
from ..services.layer_store import get_store
from .graph import get_graph
from .weather import presets_data

router = APIRouter()
_cache = ResultCache()


class FloodRequest(BaseModel):
    preset: str | None = Field(None, description="moderate | heavy | extreme | record_day")
    rain_mm_h: float | None = Field(None, gt=0, le=300)
    duration_h: float | None = Field(None, gt=0, le=48)
    condition_scale: float = Field(1.0, ge=0.3, le=1.5, description="× drain condition factors (siltation slider)")


@lru_cache
def flood_context() -> FloodContext:
    store = get_store()
    needed = {"drains", "catchments", "roads", "buildings"}
    if not needed <= store.layers.keys():
        raise HTTPException(503, "Drainage layers missing — run pipelines.build_drainage")
    return build_context({k: v.gdf for k, v in store.layers.items()}, get_graph())


def resolve(req: FloodRequest) -> dict:
    p = {"preset": None, "preset_source_id": "syn_rain"}
    if req.preset:
        pre = next((x for x in presets_data() if x["id"] == req.preset), None)
        if pre is None:
            raise HTTPException(404, f"Unknown preset {req.preset!r}")
        p.update(preset=pre["id"], rain_mm_h=pre["rain_mm_h"], duration_h=pre["duration_h"],
                 preset_source_id=pre["source_id"])
    if req.rain_mm_h is not None:
        p["rain_mm_h"] = req.rain_mm_h
    if req.duration_h is not None:
        p["duration_h"] = req.duration_h
    if "rain_mm_h" not in p or "duration_h" not in p:
        raise HTTPException(422, "Give a preset or both rain_mm_h and duration_h")
    if req.rain_mm_h is not None or req.duration_h is not None:  # custom values override the preset label
        if req.preset and (p["rain_mm_h"], p["duration_h"]) != (pre["rain_mm_h"], pre["duration_h"]):
            p["preset"], p["preset_source_id"] = None, "syn_rain"
    p["rain_mm_h"], p["duration_h"] = round(float(p["rain_mm_h"]), 2), round(float(p["duration_h"]), 2)
    p["condition_scale"] = round(req.condition_scale, 2)
    return p


@router.post("/scenarios/flood")
def scenario_flood(req: FloodRequest) -> dict:
    return _cache.get_or_run(flood_context(), resolve(req))
