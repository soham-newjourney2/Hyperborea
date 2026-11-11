# HYPERBOREA — Planning v2.0 (source of truth)

**Updated:** 6 Nov 2026 · **Supersedes:** v1.0 (archived in `docs/VISION.md` — read only when a phase file points there)
**Competition:** ISI national-level preliminary round — FIRE 2026 special session **SustAI** (Sustainable Development through AI)
**Team target:** submit + present **Thu 12 Nov 2026** · Official proposal deadline per notice: **15 Nov 2026** (13–15 Nov = buffer; verify, see §12)
**Known submission items:** PPT/PDF ≤ 20 slides · working prototype · **public prototype URL** · GitHub repo · report · demo video · literature review
**Rule from notice:** all AI used must be **open-source and free**
**Team:** 4 (user runs Claude Code; 3 teammates do non-code deliverables — `docs/TEAM_BRIEFS.md`)
**Pilot:** one small segment (~1–2 km²) of Salt Lake (Bidhannagar), Kolkata — exact boundary chosen in P02
**Role:** one Administrator with access to everything (RBAC-ready, not built)

> **Claude Code read order:** `CLAUDE.md` (auto) → this file, §10 Status first → current `phases/Pxx.md` only.

---

## 1. What we are building (one paragraph)

Hyperborea is a geospatial urban-intelligence platform: a 3D map of the pilot area whose assets (buildings, roads, drains, electrical assets, facilities, environment) live in **one shared asset + relationship model**. A **relationship engine** (NetworkX graph) propagates a hazard or a proposed development through typed dependencies and **explains every result** (path, inputs, formula, assumptions, data status). Two signature flows: **(1) extreme-rainfall cascade** — rain → drain overload → ponding → roads impassable → transformer shutdown → facility power/access loss; **(2) development assessment** — draw a building → demand vs. drainage/power/road/flood capacity → compare A (no upgrade) / B (with upgrades) / C (other site). Differentiator: the shared dependency model and honest provenance, not a pile of dashboards.

## 2. Scope rule — "full scope, hackathon level, layer by layer"

- **Every module in §3 is built**, shallow but real and working.
- **One phase = one feature/layer, finished and showcase-ready before the next starts.** A phase ends with something visible in the app that the user can demo.
- Order puts the P0 flow first so the app is always presentable; the URL goes live in P04 and is redeployed as layers are added (only on user instruction).
- Honesty over impressiveness: every value shows **Observed / Curated / Modelled / Simulated / Unknown**. Scores are indices, not probabilities. Outputs are scenario estimates, not predictions or certifications.

## 3. Modules → phase → depth

| Module | Phase | Hackathon-level implementation |
|---|---|---|
| Setup / scaffold | P01 | Vite+React+TS, FastAPI, `.venv`, `local/`, CLAUDE.md, Context7 MCP |
| Pilot boundary, buildings, roads, facilities | P02 | OSM via osmnx → GeoPackage, provenance on every feature |
| Geospatial Command Centre | P03 | CesiumJS (no ion), layer manager, asset inspector, legend, provenance badges, 2D toggle |
| Public URL | P04 | Vercel (frontend) + Hugging Face Space Docker (API), offline snapshot fallback |
| Weather + climate | P05 | Open-Meteo forecast + ERA5 archive; rainfall presets; IMD heavy-rain thresholds |
| Drainage intelligence | P06 | Simulated network along roads, DEM flow direction, Manning capacity, catchments |
| Relationship engine + explorer | P07 | NetworkX MultiDiGraph, typed edges with rules, Cytoscape explorer |
| Disaster intelligence | P08 | Rational-method runoff → routing → overflow → ponding → cascade with explained path |
| Development intelligence + what-if | P09 | Draw/select site, norms-based demand, multi-dimension checks, A/B/C compare |
| Electrical intelligence | P10 | OSM power + simulated transformers (k-means), loading, flood shutdown cascade |
| Air, water, land cover | P11 | Open-Meteo AQ (CAMS, modelled), demo water points, ESA WorldCover + NDVI |
| Transport / commute | P12 | osmnx travel times to hospital/fire/metro; flood-blocked roads → Δ access |
| CV + ML | P13 | Pretrained open water-segmentation on Sentinel-2 (fallback NDWI); sklearn surrogate risk model + model card |
| Infra health, LLM explainer, reports | P14 | Rule-based condition index; local open LLM (Ollama) grounded explainer w/ template fallback; printable report |
| Access, hardening, demo | P15 | Admin login (JWT, role field), tests, data audit, README, ARCHITECTURE, DEMO_SCRIPT, final redeploy |

Not claimed (any phase): structural safety certification, collapse prediction, real utility grid, calibrated flood model, live traffic, statutory approval.

## 4. Locked decisions (rationale in `docs/DECISIONS.md`)

| ID | Decision |
|---|---|
| D-01 | Folder `D:\hyperborea`; existing repo `github.com/soham-newjourney2/hyperborea`; branch `main` only |
| D-02 | Commits: user's existing git identity, short one-liners `Pxx: <what>`; **no Claude co-author / attribution** |
| D-03 | **No `git push` and no deploy until the user explicitly instructs** (enforced as `ask` in `.claude/settings.json`) |
| D-04 | Native Windows + PowerShell; no Docker locally (Dockerfile only for the HF Space) |
| D-05 | Everything downloaded stays in the project: Python → `.venv`, npm → `node_modules`, models/datasets/caches/tools → `local/` (gitignored). Base tools (Git, Python, Node, Claude Code) already installed system-wide |
| D-06 | Storage: GeoPackage (`data/processed/hyperborea.gpkg`) + small JSON/CSV; **no PostGIS in sprint** |
| D-07 | CesiumJS with open tiles (OSM, EOX Sentinel-2 cloudless), **no Cesium ion token**, flat ellipsoid terrain |
| D-08 | Built independently; Bilawal Sidhu's God's Eye View is visual inspiration only, no code copied |
| D-09 | Drainage + electrical networks are **simulated/curated and labelled**; never shown as municipal/utility data |
| D-10 | Hosting: Vercel (static frontend) + Hugging Face Space (FastAPI, Docker, CPU free tier). Deploy via CLI |
| D-11 | AI pieces: pretrained open CV (offline), sklearn surrogate risk model, local open LLM explainer (Ollama). All OSI-licensed; licences recorded |
| D-12 | Token economy: lean planning.md (this), one phase file per session, Context7 MCP for docs, libraries over hand-written code |
| D-13 | Non-code deliverables owned by teammates (`docs/TEAM_BRIEFS.md`); Claude Code supplies screenshots, ARCHITECTURE, DEMO_SCRIPT, LOG |

## 5. Architecture & stack

```
Vercel: React + TS + CesiumJS  ──HTTPS/JSON──▶  HF Space: FastAPI (modular monolith)
  Command Centre · Layers · Inspector              api/ → services/ → engine/
  Relationship Explorer · Disaster Lab              LayerStore (GeoPackage → memory at startup)
  Development · Environment · Reports               engine: graph · flood · power · access · development · health · risk · explain
  offline snapshots (public/snapshots)              external: Open-Meteo (cached, snapshot fallback)
                         offline pipelines/ (laptop): OSM, DEM, WorldCover, Sentinel-2, CV, surrogate training → data/processed
```

| Layer | Choice |
|---|---|
| Frontend | Vite, React, TypeScript, CesiumJS + `vite-plugin-cesium` (plain Cesium, no Resium), Zustand, Tailwind (`@tailwindcss/vite`), Recharts, Cytoscape.js |
| Backend | Python, FastAPI, Uvicorn, Pydantic v2 / pydantic-settings, GeoPandas + pyogrio, Shapely 2, pyproj, NetworkX, httpx, scikit-learn, joblib, PyJWT |
| Pipelines | osmnx, rasterio/rioxarray, pystac-client + planetary-computer (Sentinel-2, Copernicus DEM, ESA WorldCover) |
| ML (offline, P13) | PyTorch (CUDA cu128 wheels — works on RTX 40 + 50 series), Hugging Face Hub; Ollama portable for LLM |
| Tests | pytest (+ FastAPI TestClient), vitest for small pure TS utils |

Install latest stable versions at phase time; record exact versions in `docs/LOG.md`. Don't add Neo4j, Kubernetes, message brokers, extra databases.

**Repo layout** (create folders only when a phase needs them):
```
CLAUDE.md  planning.md  README.md  .gitignore  .env.example  .mcp.json  .claude/settings.json
phases/P01..P19.md     docs/{LOG,DECISIONS,DATA_SOURCES,SUBMISSION_CHECKLIST,TEAM_BRIEFS,VISION}.md
frontend/              backend/{app/{api,core,services},engine,tests,requirements.txt,Dockerfile}
pipelines/             config/ (scenarios.yaml, norms.yaml)      scripts/ (env.ps1, dev.ps1, deploy.ps1, …)
data/regions/<id>/{raw,processed,curated,synthetic,snapshots}   (id: sector_v, chennai_velachery, pune_kharadi, london_stratford, sydney_green_square)
models/regions/<id>/ (surrogate + model cards) · models/model_cards/ (shared: LLM explainer)
local/regions/<id>/{osm,rasters,cache} (OSM extract, DEM; cache ignored) · local/{tools,ollama} (LLM, ignored) · local/cache (ignored)
frontend/public/{snapshots,overlays}/regions/<id>/ + snapshots/regions.json
```
Git (updated 2026-11-07, user decision, private repo): commit everything teammates need — code, configs, docs, Claude workflow files, data (raw + processed), rasters, OSM extracts and the local LLM; files > 5 MB go through **Git LFS** (`.gitattributes`). Ignore only `.env` secrets, `.venv`, `node_modules`, `local/cache|hf|torch`, build output.

## 6. Shared data model (ask user before changing)

**CRS:** store/serve EPSG:4326; compute distances/areas in the region's UTM zone (`config/regions.yaml` `metric_crs`; Sector V = **EPSG:32645**, UTM 45N). (P16, user-approved multi-region)
**Every feature's properties (minimum):**
```
asset_id (stable, e.g. bld_osm_w123, drn_syn_0042, trf_syn_007) · asset_type · name
data_status: observed | curated | modelled | simulated | unknown
source_id (→ docs/DATA_SOURCES.md) · observed_at (ISO, tz) · ingested_at
confidence (0–1 or low/med/high) · assumptions (short text) · attrs (type-specific dict)
```
Type-specific attrs, e.g. building `height_m`, `height_status`, `levels`, `use`; drain `diameter_m`, `slope`, `manning_n`, `capacity_m3s`, `condition_factor`; transformer `rating_kva`, `load_kva`, `plinth_m`.

**Relationship (edge) fields:** `relationship_id, type, source, target, rule (how derived), weight, unit, data_status, confidence, assumptions`.
**Edge types:** `DRAINS_TO` (drain→drain/outfall) · `ADJACENT_TO` (drain↔road) · `ACCESSIBLE_VIA` (building/facility→road) · `LOCATED_WITHIN` (asset→catchment) · `SUPPLIES` (substation→transformer→building/facility) · `DEPENDS_ON` (facility→transformer/road) · `EXPOSED_TO` (asset→hazard zone, scenario only) · `PROPOSED_ADJACENT_TO` (proposed site→asset, scenario only). No edge without a `rule`.

**Scenarios never mutate the baseline** — they run on an overlay/copy; results are stored under `result_id`.

## 7. Engine rules (shared formulas; show them in the UI)

- **Runoff (rational method):** `Q [m³/s] = C · i [mm/h] · A [m²] / 3.6e6`; C: roof 0.90, road 0.85, other 0.40 (WorldCover-based C optional after P11, flag `runoff_c_source`).
- **Pipe capacity (Manning, full flow):** `Q = (1/n) · A · R^(2/3) · S^(1/2)`, n = 0.015, S = max(DEM slope, 0.002) (assumed; Salt Lake is flat), effective capacity = Q × condition_factor.
- **Routing:** topological order on `DRAINS_TO`; outflow = min(inflow, capacity); overflow = inflow − capacity.
- **Ponding:** depth = overflow × duration / (catchment area × 0.3 low-lying fraction), capped 1.0 m (assumption).
- **Thresholds (assumed, editable in `config/`):** road impaired ≥ 0.15 m, impassable ≥ 0.30 m; building plinth 0.45 m; transformer plinth 0.6 m → protective shutdown.
- **Risk index (not a probability):** `R = H^wH · E^wE · V^wV · C^wC` on 0–1 normalised components (Hazard, Exposure, Vulnerability, Consequence); weights shown; VISION §8.4.
- **Development norms (assumed, `config/norms.yaml`):** floor height 3.2 m; occupancy residential 1 p/18 m², commercial 1 p/10 m²; water 135 lpcd residential / 45 lpcd commercial (CPHEEO); electrical 15 W/m² residential / 60 W/m² commercial, diversity 0.6.
- **Development verdict:** any dimension fail → *Potentially unsuitable under current assumptions*; any conditional → *Conditionally suitable — upgrades or further assessment required*; ≥ 2 key dimensions insufficient → *Insufficient data*; else *Suitable under current assumptions*.
- **Explanation object (every result):** affected asset · trigger · path [{from, edge, to, rule, values}] · inputs + sources · formula · assumptions · data_status · confidence · mitigation · data that would improve it.

## 8. API contract (prefix `/api`; ask user before breaking changes)

| Method & path | Purpose | Phase |
|---|---|---|
| GET `/health` | status + version + data timestamp | P01 |
| GET `/region` · `/layers` · `/layers/{id}` · `/assets/{id}` | boundary, layer list (with status), GeoJSON, asset detail + edges | P03 |
| GET `/weather/current` · `/weather/forecast` · `/climate/summary` · `/scenarios/presets` | Open-Meteo (cached), ERA5 stats, rainfall presets | P05 |
| GET `/graph/summary` · `/graph/neighbors/{id}?depth=` · `/graph/path?src=&dst=` | relationship explorer | P07 |
| POST `/scenarios/flood` | {preset or rain_mm_h, duration_h, condition_scale} → result | P08 |
| POST `/development/assess` · `/development/compare` | {geometry or site_id, use, floors, upgrades[]} → verdict + checks | P09 |
| GET `/environment/air` · `/environment/water` · `/environment/landcover` | AQ (CAMS), water points, WorldCover/NDVI stats + overlays | P11 |
| GET `/access/summary` | travel times, scenario Δ | P12 |
| GET `/ml/quickscan?rain_mm_h=&duration_h=` · `/models` | surrogate predictions, model cards | P13 |
| GET `/infra-health` · POST `/explain` · GET `/report/{result_id}` | condition index, explainer, report data | P14 |
| POST `/auth/login` | admin JWT (role claim) | P15 |

**Multi-region (P16, user-approved):** every endpoint above takes optional `?region=<id>` (default `sector_v`, unknown → 404); `GET /regions` lists pilots.

Errors: `{"detail": "..."}`. Frontend `api.ts` falls back to `public/snapshots/*.json` when the API is unreachable and shows an **Offline snapshot** badge.

## 9. Local-everything paths (`scripts/env.ps1`, dot-source in every shell)

`HF_HOME=local\hf` · `TORCH_HOME=local\torch` · `PIP_CACHE_DIR=local\cache\pip` · `OLLAMA_MODELS=local\ollama\models` · `MPLCONFIGDIR=local\cache\mpl` · osmnx `settings.cache_folder=local\cache\osmnx` · `npm_config_cache=local\cache\npm` · Ollama portable in `local\tools\ollama` · tile/raster downloads in `local\tiles`, `local\rasters`. Backend `core/paths.py` sets the same defaults if unset.

## 10. Status (Claude Code updates this table)

Status values: `todo` → `in-progress` → `built` (code + tests pass) → **`done`** (user confirmed in chat — only then). Log every session in `docs/LOG.md`.

| Phase | Feature / layer | Day | Status | Confirmed |
|---|---|---|---|---|
| P01 | Setup + scaffold | Fri 6 Nov | done | 2026-11-06 |
| P02 | Pilot boundary + OSM buildings/roads/facilities | Fri 6 Nov | done | 2026-11-06 |
| P03 | 3D Command Centre | Fri 6 → Sat 7 | done | 2026-11-06 |
| P04 | Deploy (Vercel + HF Space) + snapshot fallback | Sat 7 Nov | in-progress | |
| P05 | Weather + climate | Sat 7 Nov | done | 2026-11-06 |
| P06 | Drainage network | Sun 8 Nov | done | 2026-11-06 |
| P07 | Relationship engine + explorer | Sun 8 Nov | done | 2026-11-06 |
| P08 | Disaster: rainfall cascade | Mon 9 Nov | done | 2026-11-06 |
| P09 | Development assessment + A/B/C | Mon 9 Nov | done | 2026-11-06 |
| P10 | Electrical network + cascade link | Tue 10 Nov | done | 2026-11-06 |
| P11 | Air, water, land cover | Tue 10 Nov | done | 2026-11-06 |
| P12 | Roads / commute accessibility | Tue 10 Nov | done | 2026-11-07 |
| P13 | CV layer + ML surrogate | Wed 11 Nov | done | 2026-11-07 |
| P14 | Infra health + LLM explainer + report | Wed 11 Nov | done | 2026-11-07 |
| P15 | Admin login, hardening, demo pack, final redeploy | Wed 11 Nov | done | 2026-11-07 |
| P16 | Multi-region core (registry + `?region=`) | post-qual | built | |
| P17 | Chennai (Velachery) + Pune (Kharadi) | post-qual | built | |
| P18 | London (Hackney Wick / Stratford) | post-qual | built | |
| P19 | Sydney (Green Square) + multi-region demo pack | post-qual | in-progress | |
| P20 | Open access (no login, auth off by default) | add-ons | built | |
| P21 | Live early warning (72 h forecast → cascade) | add-ons | built | |
| P22 | Validation vs real flood (Chennai 2015, Sentinel-1) | add-ons | built | |
| P23 | Upgrade optimiser (risk removed per budget) | add-ons | built | |
| P24 | Ask-the-twin chat (grounded local LLM) | add-ons | built | |

**Thu 12 Nov:** submission + presentation. **13–15 Nov:** buffer before official deadline.

## 11. Cut order if behind (never cut P02–P09, provenance, P04 URL)

1. P13 CV → NDWI spectral index (labelled "index, not ML")  2. P14 LLM → template explainer only  3. P12 → hospital access only  4. P11 water → labelled demo points only, NDVI skipped  5. P15 login → shared passcode  6. Visual polish / extra charts.

## 12. Open items

| ID | Item | Owner | Status |
|---|---|---|---|
| O-01 | Official guidelines + judging rubric → `docs/SUBMISSION_CHECKLIST.md` | Teammate C | open |
| O-02 | Confirm 12 Nov vs 15 Nov, presentation time/format, template requirements | Teammate C | open |
| O-03 | Exact pilot boundary | User + Claude Code (P02) | closed — Sector V (D-17) |
| O-04 | Any real Salt Lake drainage / pumping-station / outfall info | Teammate A | open |
| O-05 | Accounts: Hugging Face (write token), Vercel; optional OpenAQ key | User | open |
| O-06 | Which laptop is the demo machine (RTX 4050 6 GB / RTX 5050) | User | open |

## 13. After qualification

60-day plan, research question and validation design stay in `docs/VISION.md` §18–19. Revisit this file on 13 Nov.
