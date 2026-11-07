# Model card — Hyperborea flood surrogate (`ml_surrogate`)

**What it is:** a scikit-learn `HistGradientBoostingClassifier` (1.9.1) that predicts, per simulated drain,
the probability that the P08 rule engine marks it **overloaded** for a given rain intensity, duration and drain-condition
scale. It is a *fast surrogate of our own rule engine*, trained on simulated runs — **not validated on real events**.

| | |
|---|---|
| Licence | Ours (MIT, repository licence); scikit-learn BSD-3-Clause |
| Training data | 2000 Latin-hypercube runs of `run_flood` × 542 drains = 1,084,000 rows (14.8% overloaded) |
| Inputs | rain_mm_h, duration_h, condition_scale, catchment_m2, runoff_c, upstream_ca_m2, upstream_area_m2, n_upstream, capacity_m3s, condition_factor, diameter_m, slope, demand_ratio |
| Split | held-out spatial blocks (500 m grid, 5/21 blocks, 135 of 542 drains) — no drain appears in both train and test |
| Hardware | CPU, trained offline; inference on the hosted API (no GPU, no torch) |
| Size | 487 kB (`models/surrogate.joblib`) |

## Held-out metrics (spatial blocks)
| | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|
| **Surrogate** | 0.899 | 0.813 | 0.854 | 0.992 |
| Baseline — overloaded if rain ≥ 69 mm/h (tuned on train F1) | 0.207 | 0.705 | 0.32 | 0.705 |

## Permutation importance (Δ ROC-AUC, held-out sample)
| Feature | Importance |
|---|---|
| demand_ratio | 0.3357 |
| n_upstream | 0.002 |
| condition_factor | 0.0018 |
| slope | 0.0013 |
| runoff_c | 0.0005 |
| capacity_m3s | 0.0002 |
| duration_h | -0.0 |
| condition_scale | 0.0 |
| rain_mm_h | -0.0001 |
| diameter_m | -0.0001 |
| catchment_m2 | -0.0004 |
| upstream_ca_m2 | -0.0009 |
| upstream_area_m2 | -0.0017 |

## Limitations
- It reproduces a **simulated** network (P06) and an assumed rule engine (P08); it inherits every assumption of both.
- Duration does not change overload in the rational-method engine (peak flow) — any duration importance is noise.
- Outside the training ranges (rain 5–120 mm/h, duration 0.5–6 h, condition 0.6–1.2) predictions are unreliable.
- Use for instant "what-if" sliders only; the full engine (with explanations) remains the reference.
