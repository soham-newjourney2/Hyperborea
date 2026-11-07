# Submission checklist — ISI / FIRE 2026 SustAI

**Owner:** Teammate C (extract every mandatory item from the official guidelines into this file on 6 Nov).
**Team target:** Thu 12 Nov 2026 · **Official proposal deadline (per notice):** 15 Nov 2026 · verify both.

## From official guidelines (to fill — O-01)
- [ ] Guideline file saved in `docs/guidelines/`
- [ ] Problem statement / track wording copied here
- [ ] Judging rubric copied here, mapped to slides + demo moments
- [ ] Exact submission portal, time (IST), file formats, size limits
- [ ] Template requirements (PPT/report)
- [ ] Presentation format and duration (plan: 10–15 min live demo)

## Known items
| Item | Owner | Due | Status |
|---|---|---|---|
| PPT/PDF proposal, ≤ 20 slides | Teammate B | 11 Nov | ☐ |
| Working prototype | User (Claude Code) | 11 Nov | ☐ |
| Public prototype URL (Vercel + HF Space), credentials for judges | User | 11 Nov | ☐ |
| GitHub repo pushed (only on user's instruction) | User | 11–12 Nov | ☐ |
| Project report | Teammate C | 11 Nov | ☐ |
| Literature review | Teammate C | 10 Nov | ☐ |
| Demo video (backup, full flow) | Teammate B | 11 Nov | ☐ |
| AI compliance table: every model/library, licence, open-source + free ✔ | User + Teammate C | 11 Nov | ☐ |
| Data attribution list (OSM, Open-Meteo, ESA, Copernicus, EOX) | Teammate A | 11 Nov | ☐ |
| SDG mapping (9, 11, 13 primary; 6, 7 via modules) | Teammate B | 10 Nov | ☐ |

## Day-of checks (12 Nov)
- [ ] Wake the HF Space 10 min before (free Spaces sleep when idle)
- [ ] Demo laptop: app runs locally too (`scripts/dev.ps1`), offline snapshots present
- [ ] Backup video on laptop + USB
- [ ] Fixed demo scenario from `docs/DEMO_SCRIPT.md`; no untested inputs live


## AI components — open-source / free compliance (P13)
| Component | Model / method | Version | Licence | Runs where | Card |
|---|---|---|---|---|---|
| Flood surrogate | scikit-learn `HistGradientBoostingClassifier` trained by us on simulated engine runs | sklearn 1.9.1 | BSD-3-Clause (library), MIT (our model) | hosted API (CPU) | `models/model_cards/surrogate.md` |
| Surface water | NDWI spectral index (McFeeters 1996) — **not ML** (D-21) | — | public method; Copernicus Sentinel data | offline pipeline | `models/model_cards/cv_water.md` |
| Explainer — template (P14) | deterministic Python template over engine facts | — | MIT (ours) | hosted + local (default) | `models/model_cards/llm_explainer.md` |
| Explainer — local LLM (P14) | Qwen3-4B-Instruct-2507 (`qwen3:4b-instruct-2507-q4_K_M`) via Ollama v0.40.15 | 2507, 4-bit | **Apache-2.0** (model, verified on Hugging Face 2026-11-07); Ollama MIT | local only (RTX 4050, 100 % GPU) — grounding-checked, falls back to template | `models/model_cards/llm_explainer.md` |
