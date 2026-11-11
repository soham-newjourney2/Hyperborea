"""P14 endpoints: /infra-health, /explain (+ /explain/status), /report/{result_id} (planning §8)."""
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...engine import explain as ex
from ...engine import health as eh
from ..core.config import get_settings
from ..core.regions import cfg, per_region
from .access import get_access
from .scenarios import attach_access, flood_context, result_cache
from .weather import presets_data

router = APIRouter()
DEFAULT_MODEL = "qwen3:4b-instruct-2507-q4_K_M"  # Qwen3-4B-Instruct-2507, Apache-2.0, non-thinking (verified on HF 2026-11-07)
ATTRIBUTIONS = [
    "© OpenStreetMap contributors (ODbL)", "Copernicus DEM GLO-30 © DLR/Airbus, ESA",
    "ERA5 (Copernicus/ECMWF), weather and CAMS air quality via Open-Meteo.com (CC BY 4.0)",
    "© ESA WorldCover 2021 (CC BY 4.0)", "Contains modified Copernicus Sentinel data 2025–2026",
]
SIMULATED_PARTS = ["drainage network (P06)", "electrical distribution network (P10)", "rainfall presets",
                   "drain condition, asset age and inspection dates (infrastructure health)"]


def _model() -> str:
    return get_settings().ollama_model or DEFAULT_MODEL


@per_region
def health_data() -> dict:
    return eh.compute(flood_context(), presets_data(), get_access())


@router.get("/infra-health")
def infra_health(type: Literal["drain", "transformer", "road"] = "drain", top: int = Query(10, ge=1, le=200)) -> dict:
    items = health_data()[type]
    return {"type": type, "label": "Condition index 0–100 (100 = healthy) — screening index, partly simulated inputs",
            "formula": "index = 100 · (1 − Σ wᵢ·stressᵢ / Σ wᵢ)", "weights": items[0]["weights"] if items else eh.WEIGHTS,
            "simulated_inputs": [k for k, v in eh.SIMULATED.items() if v], "count": len(items), "items": items[:top]}


class ExplainRequest(BaseModel):
    result_id: str
    asset_id: str | None = None
    mode: Literal["template", "llm"] | None = None


def _result(result_id: str) -> dict:
    res = result_cache().data.get(result_id)
    if res is None:
        raise HTTPException(404, "Unknown result_id — run POST /scenarios/flood first")
    return attach_access(res)


@router.get("/explain/status")
def explain_status() -> dict:
    s = get_settings()
    st = ex.llm_status(s.ollama_url, _model())
    return {"default_mode": s.explainer, "llm": st,
            "note": "LLM runs only locally (Ollama); hosted mode uses the deterministic template"}


@router.post("/explain")
def explain(req: ExplainRequest) -> dict:
    s = get_settings()
    mode = req.mode or s.explainer
    try:
        return ex.explain(_result(req.result_id), req.asset_id, mode, s.ollama_url, _model())
    except KeyError as e:
        raise HTTPException(404, f"No explanation for {req.asset_id!r} in this result") from e


@router.get("/report/{result_id}")
def report(result_id: str) -> dict:
    res = _result(result_id)
    return {
        "result_id": result_id, "title": f"Hyperborea scenario report — {cfg()['name']}, {cfg()['city']} pilot", "region": cfg()["id"],
        "label": res["label"], "data_status": res["data_status"], "params": res["params"], "summary": res["summary"],
        "narrative": ex.template(ex.facts(res, None)),
        "affected": res["affected"][:60], "affected_total": len(res["affected"]),
        "access": res.get("access"), "assumptions": res["assumptions"], "simulated_parts": SIMULATED_PARTS,
        "limitations": ["Uniform design storms; rational-method peak flows; no hydraulic calibration.",
                        "Drainage and electrical networks are simulated, not municipal / utility records.",
                        "Travel times are free-flow estimates, not live traffic.",
                        "Risk scores are indices (0–1), not probabilities."],
        "attributions": ATTRIBUTIONS + (["Terrain: © Environment Agency copyright and/or database right 2022 (LiDAR DTM, OGL v3)"]
                                         if cfg().get("dem") == "ea_lidar_dtm" else []), "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
