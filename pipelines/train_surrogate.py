"""P13 B: train the ML surrogate of the P08 flood engine (offline, CPU, scikit-learn).

Latin-hypercube runs of run_flood (rain 5–120 mm/h, duration 0.5–6 h, condition scale 0.6–1.2) → per-drain rows →
HistGradientBoostingClassifier(overloaded). Held-out SPATIAL BLOCKS of drains (no leakage between neighbours).
Baseline: a rain-intensity threshold rule. Out: models/surrogate.joblib, models/surrogate_metrics.json,
models/model_cards/surrogate.md.   Run:  python -m pipelines.train_surrogate
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import geopandas as gpd
import joblib
import numpy as np
import sklearn
from scipy.stats import qmc
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

from backend.app.api.scenarios import flood_context
from backend.engine.flood import run_flood
from backend.engine.surrogate import FEATURES, METRICS, MODEL, drain_static, features
from backend.app.core import regions as R  # noqa: E402  (P16: HYPERBOREA_REGION → paths, CRS, timezone)

N_RUNS, SEED, BLOCK_M, TEST_SHARE = 2000, 42, 500, 0.25
BOUNDS = {"rain_mm_h": (5, 120), "duration_h": (0.5, 6), "condition_scale": (0.6, 1.2)}
CARD = R.model_dir() / "model_cards" / "surrogate.md"


def main() -> None:
    t0 = time.time()
    ctx = flood_context()
    ids, static = drain_static(ctx)
    lo, hi = zip(*BOUNDS.values())
    samples = qmc.scale(qmc.LatinHypercube(d=3, seed=SEED).random(N_RUNS), lo, hi)
    X, y, run_of = [], [], []
    for k, (rain, dur, scale) in enumerate(samples):
        res = run_flood(ctx, {"preset": None, "preset_source_id": "syn_rain", "rain_mm_h": float(rain),
                              "duration_h": float(dur), "condition_scale": float(scale)})
        X.append(features(static, rain, dur, scale))
        y.append(np.array([res["layers"]["drains"][d]["state"] == "overloaded" for d in ids]))
        run_of.append(np.full(len(ids), k))
    X, y = np.vstack(X), np.concatenate(y).astype(np.int8)
    print(f"{N_RUNS} engine runs × {len(ids)} drains = {len(y):,} rows · {y.mean():.1%} overloaded · {time.time() - t0:.0f} s")

    # spatial blocks (500 m grid of drain midpoints) → hold out 25 % of blocks
    dr = gpd.read_file(R.data_dir("processed") / "drainage.gpkg", layer="drains").set_index("asset_id").to_crs(R.metric_crs())
    mid = dr.geometry.interpolate(0.5, normalized=True).loc[ids]
    block = (np.floor(mid.x / BLOCK_M).astype(int) * 1000 + np.floor(mid.y / BLOCK_M).astype(int)).to_numpy()
    blocks = np.unique(block)
    rng = np.random.default_rng(SEED)
    test_blocks = set(rng.choice(blocks, size=max(1, round(len(blocks) * TEST_SHARE)), replace=False))
    is_test_drain = np.array([b in test_blocks for b in block])
    test = np.tile(is_test_drain, N_RUNS)
    Xtr, ytr, Xte, yte = X[~test], y[~test], X[test], y[test]

    model = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, max_leaf_nodes=31, early_stopping=True,
                                           validation_fraction=0.1, random_state=SEED)
    model.fit(Xtr, ytr)
    p = model.predict_proba(Xte)[:, 1]
    pred = p >= 0.5

    # baseline: overload if rain ≥ t (t tuned on train for F1)
    rain_tr, rain_te = Xtr[:, 0], Xte[:, 0]
    ts = np.linspace(5, 120, 116)
    t_best = max(ts, key=lambda t: f1_score(ytr, rain_tr >= t, zero_division=0))
    base = rain_te >= t_best

    def m(yt, yp, score):
        return {"precision": round(float(precision_score(yt, yp, zero_division=0)), 3),
                "recall": round(float(recall_score(yt, yp, zero_division=0)), 3),
                "f1": round(float(f1_score(yt, yp, zero_division=0)), 3),
                "roc_auc": round(float(roc_auc_score(yt, score)), 3)}

    sub = rng.choice(len(yte), size=min(40_000, len(yte)), replace=False)
    imp = permutation_importance(model, Xte[sub], yte[sub], scoring="roc_auc", n_repeats=3, random_state=SEED)
    importances = dict(sorted(((f, round(float(v), 4)) for f, v in zip(FEATURES, imp.importances_mean)),
                              key=lambda kv: -kv[1]))
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL, compress=3)
    metrics = {
        "model": "HistGradientBoostingClassifier", "sklearn": sklearn.__version__, "features": FEATURES,
        "training": {"engine_runs": N_RUNS, "rows": int(len(y)), "train_rows": int(len(ytr)), "test_rows": int(len(yte)),
                     "positive_rate": round(float(y.mean()), 4), "sampling": "Latin hypercube", "bounds": BOUNDS,
                     "split": f"held-out spatial blocks ({BLOCK_M} m grid, {len(test_blocks)}/{len(blocks)} blocks, "
                              f"{int(is_test_drain.sum())} of {len(ids)} drains)", "seed": SEED,
                     "iterations": int(model.n_iter_)},
        "surrogate": m(yte, pred, p),
        "baseline": {"rule": f"overloaded if rain ≥ {t_best:.0f} mm/h (tuned on train F1)", **m(yte, base, rain_te)},
        "permutation_importance_auc": importances,
        "model_bytes": MODEL.stat().st_size,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    METRICS.write_text(json.dumps(metrics, indent=1), encoding="utf-8")
    write_card(metrics)
    print("surrogate", metrics["surrogate"], "| baseline", metrics["baseline"])
    print("importance", list(importances.items())[:6], f"| model {MODEL.stat().st_size / 1e3:.0f} kB · {time.time() - t0:.0f} s")


def write_card(mt: dict) -> None:
    s, b, tr = mt["surrogate"], mt["baseline"], mt["training"]
    imp = "\n".join(f"| {k} | {v} |" for k, v in mt["permutation_importance_auc"].items())
    CARD.parent.mkdir(parents=True, exist_ok=True)
    CARD.write_text(f"""# Model card — Hyperborea flood surrogate (`ml_surrogate`)

**What it is:** a scikit-learn `HistGradientBoostingClassifier` ({mt['sklearn']}) that predicts, per simulated drain,
the probability that the P08 rule engine marks it **overloaded** for a given rain intensity, duration and drain-condition
scale. It is a *fast surrogate of our own rule engine*, trained on simulated runs — **not validated on real events**.

| | |
|---|---|
| Licence | Ours (MIT, repository licence); scikit-learn BSD-3-Clause |
| Training data | {tr['engine_runs']} Latin-hypercube runs of `run_flood` × 542 drains = {tr['rows']:,} rows ({tr['positive_rate']:.1%} overloaded) |
| Inputs | {', '.join(mt['features'])} |
| Split | {tr['split']} — no drain appears in both train and test |
| Hardware | CPU, trained offline; inference on the hosted API (no GPU, no torch) |
| Size | {mt['model_bytes'] / 1e3:.0f} kB (`models/surrogate.joblib`) |

## Held-out metrics (spatial blocks)
| | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|
| **Surrogate** | {s['precision']} | {s['recall']} | {s['f1']} | {s['roc_auc']} |
| Baseline — {b['rule']} | {b['precision']} | {b['recall']} | {b['f1']} | {b['roc_auc']} |

## Permutation importance (Δ ROC-AUC, held-out sample)
| Feature | Importance |
|---|---|
{imp}

## Limitations
- It reproduces a **simulated** network (P06) and an assumed rule engine (P08); it inherits every assumption of both.
- `demand_ratio` (i·ΣC·A ÷ effective capacity) is an engineered feature that already encodes the engine's own formula;
  the model mostly learns where upstream capping changes the answer. High scores therefore mean "faithful to our
  rule engine", not "accurate about real floods".
- Duration does not change overload in the rational-method engine (peak flow) — any duration importance is noise.
- Outside the training ranges (rain 5–120 mm/h, duration 0.5–6 h, condition 0.6–1.2) predictions are unreliable.
- Use for instant "what-if" sliders only; the full engine (with explanations) remains the reference.
""", encoding="utf-8")


if __name__ == "__main__":
    main()
