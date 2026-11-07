"""P16: GET /regions — pilot registry (config/regions.yaml) with data readiness."""
from fastapi import APIRouter

from ..core import regions as R

router = APIRouter()
PUBLIC = ("id", "name", "city", "admin", "country", "timezone", "metric_crs", "aq_index", "story", "bbox")


@router.get("/regions")
def list_regions() -> dict:
    out = []
    for rid, r in R.registry().items():
        out.append({**{k: r.get(k) for k in PUBLIC}, "default": rid == R.DEFAULT,
                    "status": "ready" if R.is_ready(rid) else "no-data"})
    return {"default": R.DEFAULT, "regions": out}
