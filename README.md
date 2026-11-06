# Hyperborea

Geospatial urban-intelligence prototype for a pilot of **Salt Lake Sector V (Bidhannagar), Kolkata**: a 3D command centre where buildings, roads, a simulated drainage network and critical facilities share one typed dependency graph, with an explainable extreme-rainfall cascade. Built for FIRE 2026 SustAI.

Every feature carries provenance (`data_status`: observed · curated · modelled · simulated, plus `source_id`). Simulated parts (the drainage network, rainfall presets) are labelled as such in the data and the UI; scenario results are *estimates, not predictions*, and risk scores are indices, not probabilities.

## What works (P01–P08)
| Area | What you get |
|---|---|
| Pilot data | Sector V boundary (2.83 km²), 1,510 buildings, roads, facilities, waterways, land use from OpenStreetMap (ODbL) |
| 3D command centre | CesiumJS (no ion): extruded buildings, layer manager, asset inspector with provenance, floating info tag, 2D/3D, quality toggle |
| Weather & climate | Open-Meteo current + 72 h rain; ERA5 1981–2025 rainfall record with IMD thresholds; rainfall presets |
| Drainage (simulated) | 542 drains sized by design storm, flow directions from Copernicus DEM, 7 outfalls, 540 catchments, Manning capacity |
| Relationship graph | 9.4k assets, 5k typed edges (DRAINS_TO, ADJACENT_TO, ACCESSIBLE_VIA, LOCATED_WITHIN, DEPENDS_ON), each with its rule; Cytoscape explorer |
| Disaster lab | Rainfall cascade: drain overloads → ponding → impassable roads → exposed buildings → facility access, with a "Why?" chain per asset |
| Offline | API outage → app loads frozen snapshots (amber *Offline snapshot* badge) |

## Run locally (Windows / PowerShell)
```powershell
py -3.12 -m venv .venv
. .\scripts\env.ps1                         # env vars + cache paths inside the project, activates .venv
pip install -r requirements-pipelines.txt   # API + offline pipelines
cd frontend; npm install; cd ..
.\scripts\dev.ps1                           # backend :8000 + frontend :5173
```
Processed data is committed, so the app runs without re-fetching. To rebuild it:
```powershell
python -m pipelines.fetch_osm; python -m pipelines.normalize_osm     # OSM (Geofabrik extract) → hyperborea.gpkg
python -m pipelines.fetch_dem; python -m pipelines.build_drainage    # Copernicus DEM → drainage.gpkg
python -m pipelines.climate                                          # ERA5 rainfall record
python scripts/make_snapshots.py                                     # offline snapshots (API running)
```

## Tests
`pytest -q` (backend + data integrity) · `cd frontend; npm test; npm run build`

## Docs
[Decisions](docs/DECISIONS.md) · [Data sources & licences](docs/DATA_SOURCES.md) · [Deploy](docs/DEPLOY.md)

## Attribution
© OpenStreetMap contributors (ODbL) · Copernicus DEM GLO-30 © DLR/Airbus, ESA · ERA5 (Copernicus/ECMWF) and weather data by Open-Meteo.com (CC BY 4.0) · Sentinel-2 cloudless by EOX.

Licence: MIT.
