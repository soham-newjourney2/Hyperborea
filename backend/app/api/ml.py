"""P13 endpoints: /ml/quickscan (instant surrogate map) and /models (model cards) — planning §8."""
import json
import time

from fastapi import APIRouter, HTTPException, Query

from ...engine import surrogate as sg
from ...engine.flood import run_flood
from ..core.paths import ROOT
from ..core.regions import data_dir, model_dir
from .scenarios import flood_context

router = APIRouter()
SHARED_CARDS = ROOT / "models" / "model_cards"  # region-agnostic cards (LLM explainer)


@router.get("/ml/quickscan")
def ml_quickscan(rain_mm_h: float = Query(40, gt=0, le=150), duration_h: float = Query(2, gt=0, le=12),
                 condition_scale: float = Query(1.0, ge=0.3, le=1.5), compare: bool = False) -> dict:
    ctx = flood_context()
    t0 = time.perf_counter()
    try:
        out = sg.quickscan(ctx, rain_mm_h, duration_h, condition_scale)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e)) from e
    out["inference_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    m = sg.metrics() or {}
    out["held_out"] = {"surrogate": m.get("surrogate"), "baseline": m.get("baseline")}
    if compare:  # honesty check against the full rule engine for the same slider values
        eng = run_flood(ctx, {"preset": None, "preset_source_id": "syn_rain", "rain_mm_h": rain_mm_h,
                              "duration_h": duration_h, "condition_scale": condition_scale})
        out["vs_engine"] = sg.agreement(out["probabilities"], eng["layers"]["drains"])
    return out


@router.get("/models")
def models() -> list[dict]:
    out = []
    for mid, title, mfile in (("ml_surrogate", "Flood surrogate (HistGradientBoosting)", sg.metrics_path()),
                              ("cv_water", "Surface water — NDWI spectral index (not ML)", data_dir() / "cv_water_summary.json")):
        card = model_dir() / "model_cards" / f"{'surrogate' if mid == 'ml_surrogate' else 'cv_water'}.md"
        out.append({"id": mid, "title": title, "available": card.exists(),
                    "card_markdown": card.read_text(encoding="utf-8") if card.exists() else None,
                    "metrics": json.loads(mfile.read_text(encoding="utf-8")) if mfile.exists() else None})
    return out
