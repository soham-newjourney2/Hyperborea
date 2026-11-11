# Team briefs (teammates — no Claude Code access to the repo)

Inputs from the build: screenshots (ask the user — not kept in the repo), `docs/LOG.md`, `docs/ARCHITECTURE.md` + `docs/DEMO_SCRIPT.md` (P15), model cards in `models/model_cards/`. Ask the user for the latest files; don't edit the repo directly — send files to the user.

**Honesty rules for all materials:** say *simulated* for drainage/electrical networks; *modelled* for weather/AQ/risk; risk scores are *indices, not probabilities*; outputs are *scenario estimates, not predictions or approvals*. Don't claim novelty or accuracy we haven't measured.

---

## Teammate A — Data & GIS scout (6–10 Nov)
**Goal:** improve real-world grounding of the pilot.
1. **6 Nov:** help pick the pilot boundary — for 2–3 Salt Lake candidates (e.g. Sector V; a Sector I–III residential block cluster near a canal) note: known waterlogging spots (news reports with dates), canals/outfalls, pumping stations, hospitals/fire stations, metro stations.
2. **7–8 Nov:** search for any public Bidhannagar drainage info (municipal reports, drainage maps, pumping stations, canal names, past waterlogging events with dates/locations). Deliver as a table: item, location (lat/lon or address), source URL, date.
3. **9 Nov:** any published water-quality values for the area (WBPCB/CPCB reports, papers) with parameter, unit, date, location, source. If none: say so (we'll use labelled demo data).
4. **10 Nov:** attribution list for every dataset in `docs/DATA_SOURCES.md`.
**Deliver:** `team_inputs/A_*.md` or spreadsheet to the user.

## Teammate B — Presentation & video (6–11 Nov)
**Goal:** ≤ 20-slide PPT/PDF + backup demo video.
1. **6–7 Nov:** slide skeleton following the rubric (from Teammate C) and this flow: problem → interdependent urban systems → Hyperborea idea → live demo (3D twin, rainfall cascade, development A/B/C) → architecture → AI components (CV, ML surrogate, LLM explainer, graph engine — all open-source) → data provenance & limitations → SDGs (9, 11, 13 primary; 6, 7) → 60-day roadmap → team.
2. **8–10 Nov:** drop in screenshots as they arrive; SDG slide; impact slide (who uses it: planners, municipal engineers, developers, citizens — future roles).
3. **11 Nov:** record full demo video following `docs/DEMO_SCRIPT.md` (screen recording, 1080p, ≤ the time limit); export PPT → PDF.
**Deliver:** `.pptx`, `.pdf`, `.mp4` to the user.

## Teammate C — Compliance, research & report (6–11 Nov)
**Goal:** make sure we qualify on paper.
1. **6 Nov (first thing):** read the official guidelines; fill `docs/SUBMISSION_CHECKLIST.md` (send text to the user); confirm 12 vs 15 Nov, format, time limit, templates, AI-licence rules.
2. **7–10 Nov:** literature review (topics in `docs/VISION.md` §23.2: urban digital twins, infrastructure interdependency & cascading failure, climate risk & urban resilience, geospatial graph learning, flood/drainage modelling, multi-criteria site suitability). Per paper: problem, data, method, results, limitations, relevance. 10–15 solid papers > 40 thin ones. Identify the gap from the papers, don't assume it.
3. **9–11 Nov:** project report: abstract, problem, objectives, related work, data & provenance, architecture, methods (formulas from planning §7), AI components + licences, results (screens), limitations, roadmap, references.
4. **11 Nov:** AI compliance table (model/library, licence, link).
**Deliver:** checklist text, `lit_review.docx/.pdf`, `report.docx/.pdf` to the user.
