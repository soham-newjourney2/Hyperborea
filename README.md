# Hyperborea — urban infrastructure intelligence (Salt Lake Sector V pilot)

**FIRE 2026 SustAI prototype.** Cities manage drainage, power, roads and critical services in separate tools, so nobody sees
how a heavy downpour in one place becomes a blocked ambulance route somewhere else. Hyperborea puts a bounded pilot —
**Salt Lake Sector V, Kolkata (2.83 km²)** — into one 3D digital twin where every asset shares a typed dependency graph, and
runs transparent "what-if" scenarios on it: an extreme-rainfall cascade and a proposed-development assessment, each with
a hop-by-hop **Why?** explanation.

> **Honesty first.** Every feature carries `data_status` (observed · curated · modelled · simulated) and `source_id`.
> The drainage and electrical networks are **simulated** (no public records exist) and labelled so in data and UI.
> Scenario results are *estimates, not predictions*; risk scores are *indices, not probabilities*.

## What it does
| Module | Highlights | Screens |
|---|---|---|
| 3D command centre | CesiumJS (no ion), extruded buildings, layer manager with provenance chips, inspector, floating info tag, 2D/3D, render-quality toggle | `P03_*` |
| Weather & climate | Open-Meteo live + 72 h rain; ERA5 1981–2025 rainfall record with IMD thresholds | `P05_*` |
| Drainage (simulated) | 542 drains sized by design storm, DEM flow directions, 7 outfalls, 540 catchments, Manning capacity | `P06_*` |
| Relationship graph | 9.6k assets, 7k typed edges (DRAINS_TO, ADJACENT_TO, ACCESSIBLE_VIA, LOCATED_WITHIN, DEPENDS_ON, SUPPLIES), each with its rule; Cytoscape explorer | `P07_*` |
| Disaster lab | Rain → drain overload → ponding → impassable roads → exposed buildings → transformer shutdown → facility power/access loss, with Why? chains | `P08_*`, `P10_*` |
| Development assessment | Draw or pick a site → 7 checks (drainage, flood, road, facilities, electrical, water, land use) → verdict + A/B/C comparison — never "approved" | `P09_*` |
| Electrical (simulated) | 194 transformers, schematic 11 kV feeders, OSM substations; cascade + development headroom | `P10_*` |
| Environment | CAMS air quality → India NAQI; demo water points (labelled); ESA WorldCover + Sentinel-2 NDVI overlays | `P11_*` |
| Accessibility | Free-flow drive times to hospitals / fire / metro; flood Δ and isolated pockets | `P12_*` |
| AI | ML flood surrogate (scikit-learn, held-out F1 0.85 vs 0.32 baseline) for instant sliders; NDWI water layer (index, *not* ML); optional local LLM explainer (Qwen3-4B-Instruct, Apache-2.0) with a grounding check | `P13_*`, `P14_*` |
| Reports & health | Infrastructure condition index (partly simulated inputs), printable scenario report (PDF / JSON / CSV) | `P14_*` |
| Access & resilience | Admin login (JWT, role claim); offline snapshot fallback when the API is unreachable | `P04_*`, `P15_*` |

## Architecture
React + TypeScript + CesiumJS frontend (Vercel) ↔ FastAPI modular monolith (Hugging Face Space, CPU) — layer store,
relationship graph, flood / power / access / development / health engines, explainer. Offline pipelines (laptop) build all
data into small GeoPackages and JSON. Details and diagram: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Run locally (Windows / PowerShell)
**Teammates: follow [SETUP.md](SETUP.md)** — every command, the optional local LLM, data rebuilds and troubleshooting.

```powershell
py -3.12 -m venv .venv
. .\scripts\env.ps1                         # env vars + caches inside the project, activates .venv
pip install -r requirements-pipelines.txt   # API + offline pipelines
cd frontend; npm install; cd ..
copy .env.example .env                      # then set ADMIN_PASSWORD and a ≥ 32-char JWT_SECRET
.\scripts\dev.ps1                           # backend :8000 + frontend :5173 (+ Ollama if installed)
```
Open http://localhost:5173 and sign in with `ADMIN_PASSWORD`. Processed data is committed; to rebuild it:
```powershell
python -m pipelines.fetch_osm; python -m pipelines.normalize_osm        # OSM (Geofabrik extract)
python -m pipelines.fetch_dem; python -m pipelines.build_drainage       # Copernicus DEM → simulated drainage
python -m pipelines.climate; python -m pipelines.landcover              # ERA5, WorldCover, NDVI
python -m pipelines.make_sites; python -m pipelines.build_power         # candidate sites, simulated power
python -m pipelines.make_water_demo; python -m pipelines.build_access   # demo water points, drive graph
python -m pipelines.train_surrogate; python -m pipelines.cv_water       # ML surrogate, NDWI layer
python scripts/make_snapshots.py; python scripts/audit_data.py          # offline snapshots, data audit (API running)
```
Optional local LLM: `python scripts/install_ollama.py`, then `ollama pull qwen3:4b-instruct-2507-q4_K_M` (≈ 2.5 GB, stays in `local/`).

### Environment variables (`.env`)
| Name | Purpose |
|---|---|
| `ADMIN_PASSWORD` | admin login password |
| `JWT_SECRET` | token signing secret (≥ 32 characters) |
| `CORS_ORIGINS` | allowed browser origins (comma-separated) |
| `EXPLAINER` | `template` (default) — the local LLM is chosen per request in the UI |
| `OLLAMA_URL`, `OLLAMA_MODEL` | local LLM endpoint / model (optional) |
| `VITE_API_URL` | frontend → API base URL |

## Tests
`pytest -q` — 86 tests (data integrity, engines, endpoints, auth, grounding) · `cd frontend; npm test; npm run build` ·
`python scripts/audit_data.py` → [docs/DATA_AUDIT.md](docs/DATA_AUDIT.md).

## Data, licences and attribution
Every dataset is registered in [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md); decisions in [docs/DECISIONS.md](docs/DECISIONS.md);
AI components and licences in [docs/SUBMISSION_CHECKLIST.md](docs/SUBMISSION_CHECKLIST.md) and `models/model_cards/`.
© OpenStreetMap contributors (ODbL) · Copernicus DEM GLO-30 © DLR/Airbus, ESA · ERA5 (Copernicus/ECMWF), weather and CAMS
air quality via Open-Meteo.com (CC BY 4.0) · © ESA WorldCover 2021 (CC BY 4.0) · Contains modified Copernicus Sentinel data
2025–2026 · Sentinel-2 cloudless by EOX.

## Limitations
- Drainage and electrical networks are simulated; flood depths come from a rational-method rule engine without calibration.
- Uniform design storms; ponding capped at 1 m; travel times are free-flow, not live traffic.
- Air quality is one modelled value for the pilot; water-quality points are demo data.
- The ML surrogate mirrors our own engine (not real floods); the LLM explainer can still make meaning-level slips
  (numbers are checked, meaning is not) — the deterministic template is the default.

## Roadmap (post-qualification)
Municipal drain survey + pumping stations, LiDAR terrain, calibrated hydraulics (SWMM), utility feeder data, real
water-quality and waterlogging observations, wider city coverage, and validation against recorded events.

## Team
Built for FIRE 2026 SustAI. Licence: MIT.
