"""P09 endpoints: POST /development/assess, POST /development/compare (planning §8)."""
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...engine.development import assess, what_changed
from ..services.layer_store import get_store
from .scenarios import flood_context
from .weather import presets_data

router = APIRouter()


class AssessRequest(BaseModel):
    site_id: str | None = Field(None, description="S1 | S2 | S3 or site_cur_s1 …")
    geometry: dict | None = Field(None, description="GeoJSON Polygon (EPSG:4326) — alternative to site_id")
    use: Literal["residential", "commercial"] = "commercial"
    floors: int = Field(10, ge=1, le=60)
    upgrades: list[Literal["detention", "drain_upsize", "transformer"]] = []
    design_preset: str = "design"
    label: str | None = None


class CompareRequest(BaseModel):
    options: list[AssessRequest] = Field(..., min_length=2, max_length=4)


def _run(req: AssessRequest) -> dict:
    if not req.site_id and not req.geometry:
        raise HTTPException(422, "Give site_id or geometry")
    store = get_store()
    layers = {k: v.gdf for k, v in store.layers.items()}
    try:
        res = assess(flood_context(), layers, presets_data(), req.model_dump())
    except KeyError as e:
        raise HTTPException(404, f"Unknown site or preset {e}") from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    res["label_option"] = req.label
    return res


@router.post("/development/assess")
def development_assess(req: AssessRequest) -> dict:
    return _run(req)


@router.post("/development/compare")
def development_compare(req: CompareRequest) -> dict:
    results = [_run(o) for o in req.options]
    names = [o.label or chr(65 + i) for i, o in enumerate(req.options)]
    dims = [c["dimension"] for c in results[0]["checks"]]
    table = [{"dimension": d, **{n: next(c for c in r["checks"] if c["dimension"] == d)["status"]
                                 for n, r in zip(names, results)}} for d in dims]
    return {
        "options": [{"name": n, **r} for n, r in zip(names, results)],
        "table": table,
        "verdicts": {n: r["verdict"] for n, r in zip(names, results)},
        "index": {n: r["index"]["value"] for n, r in zip(names, results)},
        "what_changed": {f"{names[0]} → {n}": what_changed(results[0], r) for n, r in zip(names[1:], results[1:])},
        "label": "Screening comparison — not an approval",
    }
