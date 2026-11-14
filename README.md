# Hyperborea — urban infrastructure digital twin

**FIRE 2026 · SustAI.** Cities run drainage, power, roads and emergency services in separate systems, so nobody sees how
a downpour in one street becomes a dark hospital or a blocked ambulance route two blocks away. Hyperborea puts five
~3 km² urban pilots into one geospatial twin where every asset is linked in a typed dependency graph, and runs
transparent "what-if" scenarios on it — each result explained hop by hop.

![Flood cascade in Salt Lake Sector V, Kolkata](docs/screenshots/02_flood_cascade.png)

> **Honest by design.** Every feature carries `data_status` (observed · curated · modelled · simulated) and a `source_id`.
> Drainage and electrical networks are **simulated** because no city publishes them — and the UI says so on the map.
> Results are scenario estimates, not predictions; risk scores are indices, not probabilities. We validated the engine
> against a real flood and publish the (unflattering) result.

## The workspace
One screen, three parts: a **module sidebar** (16 modules in six groups), a **geospatial workspace** (CesiumJS map,
satellite or street basemap, 2D or 3D) and a **module panel** beside it. A KPI strip shows the pilot's area, mapped
features and layers; the header switches pilot and theme (dark *Noir* or light *Ivory*, remembered per browser).

| Group | Module | What you get |
|---|---|---|
| Workspace | **Command Centre** | pilot overview, layer manager with provenance badges, legend, asset inspector, infrastructure health |
| | **3D Digital Twin** | the same map in 3D with extruded buildings, floating info tags, fly-to-asset |
| Analysis | **Infrastructure Intelligence** | condition index for drains, transformers and roads (modelled, not field inspections) |
| | **Dependency Graph** | typed relationships (`DRAINS_TO`, `SUPPLIES`, `DEPENDS_ON`, …) with the rule behind each edge |
| Risk & resilience | **Flood Simulation** | rain → drain overload → ponding → impassable roads → buildings above plinth → transformer shutdown → facilities without power or access, with a **Why?** chain per asset |
| | **Early Warning** | live 72 h forecast → hourly ML quick-scan → worst burst through the full engine → watch / warning banner |
| Data & planning | **Data Validation** | provenance register per layer; Chennai Dec 2015 flood seen by Sentinel-1 radar vs the engine (hit rate, false alarms, AUC) |
| | **Development Screening** | pick or draw a site → drainage, flood, road, facilities, electrical, water, land-use checks → A/B/C comparison (never an "approval") |
| | **Upgrade Optimiser** | best drain upsizes, plinth raises and detention tanks for a budget (assumed unit costs in ₹ / £ / A$) |
| | **Accessibility** | drive times to hospitals, fire stations and metro; flood-induced delays and isolated buildings |
| Environment | **Weather · Air · Water · Land cover** | Open-Meteo weather and ERA5 rainfall record; CAMS air quality in the local index (India NAQI, UK DAQI, NSW categories); demo water-quality points; WorldCover, NDVI, NDWI surface water |
| Tools | **Ask Hyperborea** | plain-language questions answered only from engine results (rule parser, or a local LLM with a numeric grounding check) + layer catalogue search |
| | **Reports** | printable scenario report (PDF / JSON / CSV) with assumptions, provenance and attribution — **Open report** after a flood run |

If the API is unreachable, the app serves **frozen snapshots** for every pilot (amber "Offline snapshot" badge).

## Screenshots
| | |
|---|---|
| ![Command centre](docs/screenshots/01_command_centre.png) **Command Centre** — Kolkata on Sentinel-2 imagery, KPI strip, infrastructure health ranking | ![Flood cascade](docs/screenshots/02_flood_cascade.png) **Flood Simulation** — extreme storm (80 mm/h × 2 h), simulated networks labelled on the map, live 72 h outlook |
| ![Validation](docs/screenshots/03_validation_chennai.png) **Data Validation** — Chennai Dec 2015 radar flood map (violet) and the engine scorecard | ![London air](docs/screenshots/04_london_air_quality.png) **Air Quality** — London in the UK DAQI, PM2.5 history + forecast, LiDAR terrain credit |
| ![Sydney 3D](docs/screenshots/05_sydney_extreme_3d.png) **3D view** — extreme-storm cascade in Green Square, Sydney | ![Pune access](docs/screenshots/06_pune_access.png) **Accessibility** — drive time to the nearest hospital per building, Pune |
| ![Ask](docs/screenshots/07_ask_the_twin.png) **Ask Hyperborea** — a grounded answer with a link to the scenario on the map | ![Light theme](docs/screenshots/08_light_theme_development.png) **Light theme** — Development Screening on the *Ivory* theme |
| ![Dependency graph](docs/screenshots/09_dependency_graph.png) **Dependency Graph** — 9,613 assets and 7,042 typed relationships in Sector V | |

## The pilots
| Pilot | Area | Buildings | Terrain | Air index | Extreme storm (80 mm/h × 2 h) |
|---|---|---|---|---|---|
| Kolkata · Salt Lake Sector V | 2.83 km² | 1,510 | Copernicus DEM 30 m | India NAQI | 90 / 542 drains overloaded · 6.6 km roads impassable |
| Chennai · Velachery | 3.07 km² | 4,748 | Copernicus DEM 30 m | India NAQI | 220 / 1,055 · 10.1 km |
| Pune · Kharadi | 3.18 km² | 1,883 | Copernicus DEM 30 m | India NAQI | 111 / 608 · 4.7 km |
| London · Hackney Wick & Stratford | 2.90 km² | 1,348 | EA LiDAR DTM 5 m | UK DAQI | 97 / 332 · 4.4 km |
| Sydney · Green Square & Alexandria | 3.12 km² | 1,318 | Copernicus DEM 30 m | NSW AQC | 83 / 405 · 6.1 km |

Buildings, roads and facilities are OpenStreetMap (observed); drains and transformers are simulated in every pilot.
Full breakdown: [docs/DATA.md](docs/DATA.md).

## Validation — what we learned
Chennai, 1–2 December 2015 (286 mm station average in 24 h). Sentinel-1 radar on 6 Dec shows flooding in 532 of 1,044
catchments: 38 % of pixels next to buildings brightened (water between walls), against 4 % on a control pass after the
water receded. With the reported rain, the engine flags 62 catchments — hit rate 6 %, false alarms 48 % — and ranks
catchments no better than chance (AUC 0.50), while simply ranking by low ground scores AUC 0.60. Cause: a regional flood
(lake releases, river overflow, marsh backwater) that a local-runoff screening engine does not model. Next step: route
overflow downhill and add lake/river inflows.

## Quick start (Windows / PowerShell)
```powershell
git lfs install
$env:GIT_LFS_SKIP_SMUDGE = "1"   # skip the ~1.7 GB of rebuild-only LFS files; setup fetches the ~12 MB the app needs
git clone https://github.com/soham-newjourney2/z-Hyperborea.git hyperborea; cd hyperborea
Remove-Item Env:GIT_LFS_SKIP_SMUDGE
.\scripts\setup.ps1            # run-only data + .venv + Python and npm packages + .env (add -Full to rebuild data)
. .\scripts\env.ps1            # every new shell: caches inside the project, activates .venv
.\scripts\dev.ps1              # API :8000 + web :5173 (+ local LLM if installed)
```
Open <http://localhost:5173> — no login by default. Everything installs **inside the project folder** (`.venv`,
`frontend/node_modules`, caches and optional portable Python / Node in `local/`). Step-by-step guide, deep links,
optional local LLM and data rebuilds: [docs/SETUP.md](docs/SETUP.md).

## Architecture
React 19 + TypeScript + CesiumJS frontend (module workspace shell) ↔ FastAPI modular monolith (layer store,
relationship graph, flood / power / access / development engines, ML surrogate, warning, optimiser, validation,
explainer) ↔ per-region GeoPackages built by offline Python pipelines. Regions are pure configuration
(`config/regions.yaml`). Runs locally; no cloud services are required. Details, diagram and API list:
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

| Layer | Stack |
|---|---|
| Frontend | React 19, TypeScript, Vite, CesiumJS (no ion), Tailwind 4, Zustand, Recharts, Cytoscape |
| Backend | Python 3.12, FastAPI, GeoPandas, Shapely, NetworkX, scikit-learn, PyJWT (optional login) |
| Pipelines | osmnx + pyosmium, rasterio / rioxarray, pystac-client + Planetary Computer, scipy |
| AI | scikit-learn flood surrogate (per region); optional local LLM Qwen3-4B-Instruct-2507 via Ollama (Apache-2.0 / MIT) |

## Repository layout
```
backend/      FastAPI app (app/), engines (engine/), tests (tests/)
frontend/     React + Cesium web app (src/), offline snapshots and overlays (public/)
pipelines/    offline data builders, one module per step
config/       regions and engine thresholds (YAML)
data/         per-region data: processed/ (served), curated/, synthetic/, snapshots/, raw/ (rebuild only)
models/       per-region flood surrogate + model cards
local/        per-region OSM extracts and DEMs (rebuild only); caches and portable tools (git-ignored)
scripts/      setup, env, dev, region build, snapshots, data audit, Ollama installer
docs/         setup guide, architecture, data sources, screenshots
```

## Configuration
| `.env` variable | Purpose |
|---|---|
| `AUTH_REQUIRED` | `false` (default): open access · `true`: admin login with `ADMIN_PASSWORD` + `JWT_SECRET` (≥ 32 chars) |
| `CORS_ORIGINS` | allowed browser origins |
| `EXPLAINER` | `template` (default) or `ollama` |
| `OLLAMA_URL`, `OLLAMA_MODEL` | local LLM endpoint and model |
| `VITE_API_URL` | frontend → API base URL |

Engine thresholds and assumptions are plain YAML in `config/` (flood, risk, scenarios, norms, warning, costs, air-quality
bands, regions).

## Tests and checks
```powershell
pytest backend/tests -q                                   # 138 tests: engines, endpoints, regions, add-ons
cd frontend; npm run lint; npm test; npm run build; cd ..  # oxlint, vitest (9 tests), type-check + production build
python scripts/audit_data.py                              # provenance audit of all five pilots (must say PASS)
```

## Limitations
- Drainage and electrical networks are simulated; the flood engine is a rule-based screening model (rational method,
  Manning, local ponding capped at 1 m) without rivers, lakes, tides, pumps or calibration.
- Uniform design storms; travel times are free-flow; air quality is one modelled value per pilot; water-quality points
  are demo data; development norms are Indian defaults in every pilot.
- ERA5 (~25 km) smooths local cloudbursts; the ML surrogate imitates our engine, not real floods; the LLM can still slip
  in meaning (numbers are checked, meaning is not) — template answers are the default.
- The satellite basemap is Sentinel-2 cloudless (EOX, ~10 m), not live or high-resolution imagery; basemaps need
  internet access.

## Roadmap
Downhill overflow routing and lake/river inflows · real drain surveys and pumping stations for one city · utility
transformer data (UK Power Networks open data needs only an account) · rain-gauge feeds · live traffic · more validation
events (Sentinel-1 for Kolkata and Sydney floods) · city-specific planning norms.

## Data and attribution
© OpenStreetMap contributors (ODbL) · Copernicus DEM GLO-30 © DLR/Airbus, ESA · © Environment Agency 2022 (OGL v3) ·
ERA5 (Copernicus/ECMWF), weather and CAMS air quality via Open-Meteo.com (CC BY 4.0) · © ESA WorldCover 2021 (CC BY 4.0) ·
Contains modified Copernicus Sentinel data 2015–2026 · Sentinel-2 cloudless by EOX. Sources, licences and processing:
[docs/DATA.md](docs/DATA.md).

## Licence
Code: MIT (see [LICENSE](LICENSE)). Data keeps the licence of its source.
