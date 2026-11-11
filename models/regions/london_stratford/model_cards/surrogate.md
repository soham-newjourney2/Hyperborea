# Model card — Hyperborea flood surrogate (`ml_surrogate`)

**What it is:** a scikit-learn `HistGradientBoostingClassifier` (1.9.1) that predicts, per simulated drain,
the probability that the P08 rule engine marks it **overloaded** for a given rain intensity, duration and drain-condition
scale. It is a *fast surrogate of our own rule engine*, trained on simulated runs — **not validated on real events**.

| | |
|---|---|
| Licence | Ours (MIT, repository licence); scikit-learn BSD-3-Clause |
| Training data | 2000 Latin-hypercube runs of `run_flood` × 542 drains = 664,000 rows (23.7% overloaded) |
| Inputs | rain_mm_h, duration_h, condition_scale, catchment_m2, runoff_c, upstream_ca_m2, upstream_area_m2, n_upstream, capacity_m3s, condition_factor, diameter_m, slope, demand_ratio |
| Split | held-out spatial blocks (500 m grid, 5/20 blocks, 89 of 332 drains) — no drain appears in both train and test |
| Hardware | CPU, trained offline; inference on the hosted API (no GPU, no torch) |
| Size | 251 kB (`models/surrogate.joblib`) |

## Held-out metrics (spatial blocks)
| | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|
| **Surrogate** | 0.859 | 0.986 | 0.918 | 0.981 |
| Baseline — overloaded if rain ≥ 57 mm/h (tuned on train F1) | 0.455 | 0.791 | 0.578 | 0.735 |

## Permutation importance (Δ ROC-AUC, held-out sample)
| Feature | Importance |
|---|---|
| demand_ratio | 0.38 |
| condition_factor | 0.0071 |
| capacity_m3s | 0.0059 |
| catchment_m2 | 0.0047 |
| slope | 0.0047 |
| runoff_c | 0.0017 |
| upstream_ca_m2 | 0.0005 |
| rain_mm_h | 0.0004 |
| n_upstream | 0.0004 |
| diameter_m | 0.0003 |
| condition_scale | 0.0002 |
| duration_h | 0.0 |
| upstream_area_m2 | -0.0006 |

## Limitations
- It reproduces a **simulated** network (P06) and an assumed rule engine (P08); it inherits every assumption of both.
- `demand_ratio` (i·ΣC·A ÷ effective capacity) is an engineered feature that already encodes the engine's own formula;
  the model mostly learns where upstream capping changes the answer. High scores therefore mean "faithful to our
  rule engine", not "accurate about real floods".
- Duration does not change overload in the rational-method engine (peak flow) — any duration importance is noise.
- Outside the training ranges (rain 5–120 mm/h, duration 0.5–6 h, condition 0.6–1.2) predictions are unreliable.
- Use for instant "what-if" sliders only; the full engine (with explanations) remains the reference.
