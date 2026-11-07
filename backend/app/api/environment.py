"""P11 endpoints: /environment/air, /environment/water, /environment/landcover (planning §8)."""
import json

from fastapi import APIRouter, HTTPException

from ..core.regions import data_dir, per_region
from ..services.air import AirUnavailable, get_air
from ..services.layer_store import get_store

router = APIRouter()


@router.get("/environment/air")
def environment_air() -> dict:
    region = get_store().region()
    if region is None:
        raise HTTPException(503, "No region loaded")
    lon, lat = region["centroid"]
    try:
        return get_air(lat, lon)
    except AirUnavailable as e:
        raise HTTPException(503, str(e)) from e


@router.get("/environment/water")
def environment_water() -> dict:
    lyr = get_store().layers.get("water_quality")
    if lyr is None:
        raise HTTPException(503, "No water-quality layer")
    gj = json.loads(lyr.full)
    statuses = sorted({f["properties"]["data_status"] for f in gj["features"]})
    demo = statuses == ["simulated"]
    return {"data_status": statuses, "demo": demo,
            "banner": "DEMO DATA — simulated water-quality values, not measurements" if demo else "Curated measurements",
            "note": "Sampling points only — values are never interpolated between points", "points": gj}


@per_region
def landcover_stats() -> dict | None:
    p = data_dir() / "landcover_stats.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


@router.get("/environment/landcover")
def environment_landcover() -> dict:
    s = landcover_stats()
    if s is None:
        raise HTTPException(503, "Land-cover stats missing — run pipelines.landcover")
    return s
