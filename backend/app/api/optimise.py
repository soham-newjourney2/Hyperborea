"""P23: POST /optimise — best upgrades per budget for a flood scenario in the active region."""
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...engine.optimise import optimise
from ..core.paths import CONFIG
from ..core.regions import current
from .scenarios import FloodRequest, flood_context, resolve

router = APIRouter()


class OptimiseRequest(BaseModel):
    preset: str = Field("extreme", description="flood preset to protect against")
    budget: float | None = Field(None, gt=0, description="in the region's currency; default from config/costs.yaml")
    with_map: bool = Field(False, description="include the post-upgrade engine result for the map")


def costs() -> dict:
    return yaml.safe_load((CONFIG / "costs.yaml").read_text(encoding="utf-8"))


@router.get("/optimise/config")
def optimise_config() -> dict:
    cfg = costs()
    code = cfg["currency_by_region"].get(current(), "INR")
    return {"currency": code, **cfg["currencies"][code], "objective": cfg["objective"],
            "note": "Assumed unit costs and value weights — edit config/costs.yaml"}


@router.post("/optimise")
def post_optimise(req: OptimiseRequest) -> dict:
    cfg = costs()
    code = cfg["currency_by_region"].get(current(), "INR")
    cur = cfg["currencies"][code]
    params = resolve(FloodRequest(preset=req.preset))
    try:
        out = optimise(flood_context(), params, req.budget or cur["default_budget"], cfg, cur)
    except KeyError as e:
        raise HTTPException(422, f"Missing data for optimisation: {e}") from e
    after = out.pop("after_result")
    out.update(region=current(), currency=code, symbol=cur["symbol"])
    if req.with_map:
        after = {**after, "result_id": f"{after['result_id']}_opt", "label": after["label"] + " · after upgrades"}
        out["after_result"] = after
    return out
