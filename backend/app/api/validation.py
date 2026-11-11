"""P22: GET /validation — engine vs an observed flood (Sentinel-1) for the active region, if an event was scored."""
import json

from fastapi import APIRouter, HTTPException

from ..core.regions import data_dir

router = APIRouter()


@router.get("/validation")
def validation() -> dict:
    p = data_dir() / "validation.json"
    if not p.exists():
        raise HTTPException(404, "No validation event for this region yet (pipelines.validate_flood)")
    return json.loads(p.read_text(encoding="utf-8"))
