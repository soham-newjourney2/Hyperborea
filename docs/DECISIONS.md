# Decisions

Short records. New decisions get the next ID and also a one-line row in planning.md §4 if they change scope/stack.

| ID | Date | Decision | Why |
|---|---|---|---|
| D-01 | 2026-11-02 | `D:\hyperborea`, existing GitHub repo, `main` only | 1 person drives the repo; branches add overhead in a 6-day sprint |
| D-02 | 2026-11-02 | Short one-line commits, user's git identity, no Claude co-author | User rule |
| D-03 | 2026-11-06 | No push / no deploy without explicit instruction | User rule; enforced via `ask` permissions |
| D-04 | 2026-11-06 | Native Windows, no local Docker | Docker Desktop + WSL2 costs setup time and RAM |
| D-05 | 2026-11-06 | All downloads inside project (`.venv`, `node_modules`, `local/`) | User rule; portable, easy cleanup |
| D-06 | 2026-11-02 | GeoPackage, no PostGIS for sprint | Pilot is small; no DB server to install/host; GeoPandas reads it directly |
| D-07 | 2026-11-02 | CesiumJS without ion token; OSM + EOX tiles, flat terrain | No account dependency; Salt Lake is flat |
| D-08 | 2026-11-02 | Independent build; God's Eye as inspiration only | Avoid licence/integration risk |
| D-09 | 2026-11-02 | Drainage + electrical simulated/curated, labelled | No public network topology for Salt Lake |
| D-10 | 2026-11-06 | Vercel + Hugging Face Space (Docker, CPU) | Free; HF Space has enough RAM for GeoPandas/NetworkX/sklearn; CLI deploy without GitHub push |
| D-11 | 2026-11-06 | AI: pretrained open CV (offline), sklearn surrogate, Ollama LLM (local; template on hosted URL) | SustAI requires open-source/free AI; hosted CPU can't run LLM/CV well |
| D-12 | 2026-11-06 | Lean planning.md; v1.0 archived as VISION.md | Claude Code reads planning every session — token cost |
| D-13 | 2026-11-06 | Teammates own PPT/report/video/lit review | Only the user runs Claude Code |
| D-14 | 2026-11-06 | Backend modular monolith: `backend/app` (API) + `backend/engine` (intelligence) + `pipelines/` (offline) | Replaces v1.0 `intelligence/` top-level folder; one deployable unit |
| D-15 | 2026-11-06 | 2D view = Cesium `SCENE2D` morph (no separate Leaflet/MapLibre) | Zero extra dependency; same layers |
| D-16 | 2026-11-06 | Flood model = rational method + Manning + simple ponding; SWMM deferred | Transparent, testable in hours; SWMM needs calibrated inputs we don't have |
| D-17 | 2026-11-06 | Pilot boundary = **Salt Lake Sector V** (2.83 km², `data/curated/boundary.geojson`); OSM fetched for boundary + 2 km buffer | User pick from P02 scan (III 3.77 km² / V 2.85 / III+V 6.61). V: IT/commercial development story (P09), wetland edge for drainage/flood (P06/P08), fewest buildings → lightest 3D. Outline is curated from OSM road cells + block labels (no official polygon in OSM) |
| D-18 | 2026-11-06 | Processed GPKG keeps **pilot-only buildings** (1,510) and no spatial index → 4.5 MB; other layers keep the 2 km buffer | 5 MB commit rule; map only shows pilot buildings; API holds layers in memory (no rtree needed). Buffer buildings remain in `data/raw/osm/<stamp>/buildings.gpkg` if a later phase needs them. User approved |
| D-19 | 2026-11-06 | Drainage outfalls: manholes ≤ 80 m from OSM canals (≥ 300 m apart); fragments without a canal may discharge to a pond/wetland/canal polygon ≤ 80 m | User choice from P06 preview (outfall 06 had no canal within 1.25 km; it now discharges to Keshtopur Canal polygon). Replace with real outfalls/pumping stations if Teammate A delivers (O-04) |
| D-20 | 2026-11-06 | Simulated drains sized by **design storm**: smallest standard pipe (0.6–2.4 m) carrying 20 mm/h on upstream ΣC·A (rational + Manning), never below road-class minimum | Road-class-only sizing put ~1 km² on a 0.9 m drain → even a 15 mm/h shower overflowed trunks (unrealistic, fails P08 acceptance). 24/542 drains upsized. Design intensity is an assumption (Salt Lake standard unknown) — editable in `build_drainage.py` |
| D-21 | 2026-11-07 | P13 CV layer = **NDWI (McFeeters) spectral index**, labelled "not ML"; Prithvi-EO deferred | User choice: avoid ~4–5 GB torch/CUDA + model download; planning §11 cut order #1. The ML surrogate (sklearn) remains the AI component. Layer/UI/model card ready for a model swap |
| D-22 | 2026-11-07 | **Multi-region**: add Chennai Velachery (TN), Pune Kharadi (MH), London Hackney Wick/Stratford (UK), Sydney Green Square/Alexandria (NSW) beside Sector V; optional `?region=` (default `sector_v`); per-region UTM metric CRS + timezone; Sector V data stays in `data/processed/`, others in `data/processed/regions/<id>/`; curated ~3 km² study rectangles | User choice (regions + API style). Areas picked by Claude for flood relevance: Velachery lake basin (2015/2023 floods), Kharadi riverside IT corridor, Hackney Wick/Stratford (July 2021 flash floods; EA LiDAR + RoFSW + UKPN open data), Green Square (former Sheas Creek wetland, City of Sydney flood studies). Real local data replaces simulated layers only where open + machine-readable |
