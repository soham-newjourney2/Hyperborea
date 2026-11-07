"""P13 ML surrogate of the P08 rule engine: per-drain overload probability from drain + scenario features.

Shared by training (pipelines/train_surrogate.py) and the API (/ml/quickscan) so features are identical.
scikit-learn only — no torch in the backend runtime.
"""
from __future__ import annotations

import json

import joblib
import numpy as np

from ..app.core.regions import model_dir, per_region
from .flood import FloodContext

# Region of this process at import (pipelines: HYPERBOREA_REGION); the API resolves per request below.
MODEL = model_dir() / "surrogate.joblib"
METRICS = model_dir() / "surrogate_metrics.json"


def model_path():
    return model_dir() / "surrogate.joblib"


def metrics_path():
    return model_dir() / "surrogate_metrics.json"
LABEL = "Surrogate of the rule engine, trained on simulated runs — not validated on real events"
FEATURES = [
    "rain_mm_h", "duration_h", "condition_scale",            # scenario
    "catchment_m2", "runoff_c", "upstream_ca_m2", "upstream_area_m2", "n_upstream",  # hydrology
    "capacity_m3s", "condition_factor", "diameter_m", "slope",  # drain
    "demand_ratio",                                           # i·ΣCA/3.6e6 ÷ (capacity × condition × scale)
]


def drain_static(ctx: FloodContext) -> tuple[list[str], np.ndarray]:
    """Per-drain static features in ctx.order: catchment_m2 … slope (scenario-independent)."""
    ids, rows = [], []
    for d in ctx.order:
        v = ctx.drain[d]
        c = ctx.cat.get(v["catchment_id"]) or {"area_m2": 0.0, "runoff_c": 0.0}
        rows.append([c["area_m2"], c["runoff_c"], v.get("upstream_ca_m2") or 0.0, v.get("upstream_area_m2") or 0.0,
                     v.get("n_upstream") or 0, v["capacity_m3s"], v["condition_factor"], v["diameter_m"], v["slope"]])
        ids.append(d)
    return ids, np.asarray(rows, dtype=np.float64)


def features(static: np.ndarray, rain: float, dur: float, scale: float) -> np.ndarray:
    n = len(static)
    cap_eff = static[:, 5] * np.clip(static[:, 6] * scale, 0.05, 1.0)
    demand = rain * static[:, 2] / 3.6e6
    scen = np.column_stack([np.full(n, rain), np.full(n, dur), np.full(n, scale)])
    return np.column_stack([scen, static, demand / np.maximum(cap_eff, 1e-9)]).astype(np.float32)


@per_region
def load_model():
    p = model_path()
    return joblib.load(p) if p.exists() else None


@per_region
def metrics() -> dict | None:
    p = metrics_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def quickscan(ctx: FloodContext, rain: float, dur: float, scale: float) -> dict:
    model = load_model()
    if model is None:
        raise FileNotFoundError("models/surrogate.joblib missing — run pipelines.train_surrogate")
    ids, static = _static(ctx)
    p = model.predict_proba(features(static, rain, dur, scale))[:, 1]
    return {"label": LABEL, "data_status": "modelled", "source_id": "ml_surrogate",
            "params": {"rain_mm_h": rain, "duration_h": dur, "condition_scale": scale},
            "probabilities": {d: round(float(x), 3) for d, x in zip(ids, p)},
            "expected_overloads": round(float(p.sum()), 1), "predicted_overloads": int((p >= 0.5).sum()),
            "drains": len(ids), "threshold": 0.5}


_cache: dict[int, tuple[list[str], np.ndarray]] = {}


def _static(ctx: FloodContext) -> tuple[list[str], np.ndarray]:
    k = id(ctx)
    if k not in _cache:
        _cache[k] = drain_static(ctx)
    return _cache[k]


def agreement(prob: dict[str, float], engine_drains: dict[str, dict]) -> dict:
    tp = fp = fn = tn = 0
    for d, p in prob.items():
        pred, true = p >= 0.5, engine_drains[d]["state"] == "overloaded"
        tp += pred and true
        fp += pred and not true
        fn += (not pred) and true
        tn += (not pred) and (not true)
    n = tp + fp + fn + tn
    return {"engine_overloads": tp + fn, "surrogate_overloads": tp + fp, "agreement_pct": round(100 * (tp + tn) / n, 1),
            "precision": round(tp / (tp + fp), 3) if tp + fp else None, "recall": round(tp / (tp + fn), 3) if tp + fn else None,
            "f1": round(2 * tp / (2 * tp + fp + fn), 3) if tp else (1.0 if fp + fn == 0 else 0.0)}
