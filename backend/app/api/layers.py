"""P03 endpoints: /region, /layers, /layers/{id}, /assets/{id} (planning §8)."""
from fastapi import APIRouter, HTTPException, Response

from ...engine.graph import relationships_of
from ..services.layer_store import get_store
from .graph import get_graph

router = APIRouter()
GEOJSON = "application/geo+json"


@router.get("/region")
def region() -> dict:
    r = get_store().region()
    if r is None:
        raise HTTPException(503, "No data loaded — run the P02 pipelines")
    return r


@router.get("/layers")
def layers() -> list[dict]:
    return [layer.meta() for layer in get_store().layers.values()]


@router.get("/layers/{layer_id}")
def layer(layer_id: str, in_pilot: bool = False) -> Response:
    lyr = get_store().layers.get(layer_id)
    if lyr is None:
        raise HTTPException(404, f"Unknown layer {layer_id!r}")
    return Response(lyr.pilot if in_pilot else lyr.full, media_type=GEOJSON,
                    headers={"Cache-Control": "public, max-age=300"})


@router.get("/assets/{asset_id}")
def asset(asset_id: str) -> dict:
    a = get_store().asset(asset_id)
    if a is None:
        raise HTTPException(404, f"Unknown asset {asset_id!r}")
    a["relationships"] = relationships_of(get_graph(), asset_id)  # P07
    return a
