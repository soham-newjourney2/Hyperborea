# Data sources register

Every dataset gets an entry **before** use. `source_id` in feature properties must match an ID here. Licences below are what we expect — **verify on the provider page and update `Verified`**.

Template:
```
### <source_id> — <name>
- Provider / access: …            - Licence / terms: …           - Verified: yes/no (date)
- Accessed: YYYY-MM-DD             - Coverage (space/time): …      - CRS / units: …
- data_status: observed|curated|modelled|simulated   - Used by: Pxx / module
- Processing: script + steps       - Quality / limitations: …
- Attribution text shown in UI: …
```

## Candidates (fill on first use)

| source_id | Dataset | Access | Expected licence / attribution | Status | Phase |
|---|---|---|---|---|---|
| osm | OpenStreetMap buildings, roads, amenities, power, waterways | osmnx / Overpass | ODbL 1.0 — "© OpenStreetMap contributors" | observed | P02 |
| osm_tiles | OSM standard raster tiles | tile.openstreetmap.org | Tile usage policy, attribution required; light demo use only | — | P03 |
| eox_s2c | EOX Sentinel-2 cloudless tiles | tiles.maps.eox.at WMTS | CC BY-NC-SA 4.0 (2018+ layers) — "Sentinel-2 cloudless by EOX" | — | P03 |
| om_forecast | Open-Meteo forecast API | api.open-meteo.com | Free non-commercial, data CC BY 4.0 — "Weather data by Open-Meteo.com" | modelled | P05 |
| om_archive | Open-Meteo historical (ERA5 reanalysis) | archive-api.open-meteo.com | CC BY 4.0; ERA5 via Copernicus | modelled | P05 |
| imd_thresholds | IMD rainfall intensity categories (heavy ≥ 64.5 mm/day …) | IMD publications | cite source | curated | P05 |
| cop_dem | Copernicus DEM GLO-30 | Planetary Computer STAC `cop-dem-glo-30` | Copernicus DEM licence, attribution required | observed | P06 |
| syn_drain | Hyperborea simulated drainage network | `pipelines/build_drainage.py` | Ours | simulated | P06 |
| cur_outfall | Outfalls placed at OSM canals/waterways by team | manual + OSM | ODbL-derived | curated | P06 |
| syn_power | Hyperborea simulated transformers / feeders | `pipelines/build_power.py` | Ours | simulated | P10 |
| om_aq | Open-Meteo Air Quality (CAMS model) | air-quality-api.open-meteo.com | CC BY 4.0; CAMS attribution | modelled | P11 |
| openaq | OpenAQ v3 station data (optional, key) | api.openaq.org | per-source licence | observed | P11 |
| esa_wc | ESA WorldCover 10 m (2021) | Planetary Computer `esa-worldcover` | CC BY 4.0 — "© ESA WorldCover project / Contains modified Copernicus Sentinel data" | observed | P11 |
| s2_l2a | Sentinel-2 L2A scenes | Planetary Computer `sentinel-2-l2a` | Copernicus open data — "Contains modified Copernicus Sentinel data <year>" | observed | P11, P13 |
| syn_water | Demo water-quality points | `data/synthetic/water_quality.geojson` | Ours | simulated | P11 |
| cur_sites | Candidate development sites | `data/curated/sites.geojson` | Ours (from OSM/imagery) | curated | P09 |
| norms | Planning norms (CPHEEO water lpcd, NBC occupancy, assumed W/m²) | `config/norms.yaml` | cite each | curated | P09 |
| cv_water | CV water segmentation output | `pipelines/cv_water.py` | model licence (see model card) | modelled | P13 |
| ml_surrogate | Surrogate risk model output | `pipelines/train_surrogate.py` | Ours | modelled | P13 |

## Registered sources

### osm — OpenStreetMap (buildings, drive/walk roads, amenities, rail/metro, power, waterways + water bodies, landuse)
- Provider / access: OpenStreetMap. Primary: Geofabrik extract `asia/india/eastern-zone-261104.osm.pbf` (OSM data as of 2026-11-05 14:54 UTC; 248 MB in `local/osm/`), clipped with pyosmium 4.3.2 (`pipelines/osm_pbf.py`). Alt: Overpass API via osmnx 2.1.1 (`fetch_osm.py overpass`; public mirrors were down/502 on 2026-11-06)   - Licence / terms: ODbL 1.0   - Verified: yes (osm.org/copyright, 2026-11-06)
- Accessed: 2026-11-06 (exact time in `data/raw/osm/<stamp>/meta.json`)   - Coverage: Sector V pilot + 2 km buffer; snapshot of OSM at fetch time   - CRS / units: EPSG:4326; lengths/areas computed in EPSG:32645
- data_status: observed (building height: `observed` from `height` tag / `modelled` = levels × 3.2 m / `assumed` 9 m default, in `attrs.height_status`)   - Used by: P02 → all modules
- Processing: `pipelines/fetch_osm.py` (raw, timestamped, immutable) → `pipelines/normalize_osm.py` (make_valid, dedupe by id + geometry, provenance props, `in_pilot` flag) → `data/processed/hyperborea.gpkg`
- Quality / limitations: pilot: 0 of 1,510 buildings carry a `height` tag, 11 (0.7 %) carry `building:levels`, 1,499 use the 9 m default; footprints incomplete in informal areas; facility points are representative points of footprints; no drainage/power network topology in OSM
- Attribution text shown in UI: "© OpenStreetMap contributors (ODbL)"
- **P17+ regions (D-22)**: same pipeline, per-region extract from `config/regions.yaml` `osm_pbf`: Chennai Velachery ← `asia/india/southern-zone-261105.osm.pbf` (559 MB), Pune Kharadi ← `asia/india/western-zone-261105.osm.pbf` (222 MB); Geofabrik builds of 2026-11-06 (exact OSM timestamp from the pbf header in `data/raw/regions/<id>/osm/<stamp>/meta.json`). Metric CRS per region (UTM 44N / 43N). Licence ODbL 1.0 (same). Accessed 2026-11-07.

### cur_boundary — Hyperborea pilot boundary (Salt Lake Sector V)
- Provider / access: ours — `pipelines/scan_candidates.py` + `pipelines/make_boundary.py`   - Licence / terms: ODbL-derived (built from OSM)   - Verified: n/a
- Accessed: 2026-11-06   - Coverage: 2.83 km², one polygon   - CRS / units: EPSG:4326
- data_status: curated   - Used by: P02 onward (D-17)
- Processing: polygonize OSM roads in the Bidhannagar ∩ study window → assign each cell to the nearest `"XX Block"` place label (≤ 450 m) → dissolve Sector V blocks (AN AP AQ BN CN CP DN DP EM EN GN GP HM) → drop slivers < 2 % of largest part
- Quality / limitations: not an official municipal boundary; edges follow roads, block membership from the Salt Lake block grid
- Attribution text shown in UI: "Pilot boundary: Hyperborea (derived from © OpenStreetMap contributors)"
- **P16+ regions (D-22)**: Chennai Velachery 3.07 km², Pune Kharadi 3.18 km², London Hackney Wick & Stratford 2.90 km², Sydney Green Square & Alexandria 3.12 km² — curated **study rectangles** (`config/regions.yaml` `bbox`, `pipelines/make_region_boundary.py`, confidence low), not official or ward boundaries; chosen by Hyperborea for flood relevance.

### om_forecast — Open-Meteo Forecast API (current + 72 h hourly)
- Provider / access: api.open-meteo.com `/v1/forecast` (no key), `backend/app/services/weather.py`   - Licence / terms: data CC BY 4.0; free API for non-commercial use   - Verified: yes (open-meteo.com licence page, 2026-11-06)
- Accessed: live, cached 30 min (`local/cache/weather.json`); offline fallback `data/snapshots/weather.json`   - Coverage: pilot centroid (model grid point 22.60 N, 88.41 E), now → +72 h   - CRS / units: WGS84; °C, %, mm, km/h, WMO code
- data_status: modelled (NWP forecast blend, Open-Meteo "best match")   - Used by: P05 weather panel, status chip
- Processing: none beyond flattening hourly arrays; WMO code → text
- Quality / limitations: model forecast, not observation; single point for the whole pilot
- Attribution text shown in UI: "Weather data by Open-Meteo.com"

### om_archive — Open-Meteo Historical API (ERA5 reanalysis, daily)
- Provider / access: archive-api.open-meteo.com `/v1/archive?models=era5`, `pipelines/climate.py`   - Licence / terms: CC BY 4.0; ERA5 © ECMWF / Copernicus Climate Change Service   - Verified: yes (2026-11-06)
- Accessed: 2026-11-06   - Coverage: ERA5 grid cell 22.50 N, 88.50 E (~0.25°); 1981-01-01 → 2026-10-31 (stats on full years 1981–2025)   - CRS / units: WGS84; mm/day, °C
- data_status: modelled (reanalysis)   - Used by: P05 climate charts, `record_day` preset (P08)
- Processing: annual total, JJAS total, annual max 1-day, IMD-class day counts, OLS trend per decade (scipy linregress) → `data/processed/climate_{daily.csv,summary.json}`
- Quality / limitations: grid-cell averages smooth convective extremes (max 1-day 169.9 mm, 2019-08-17) — station records are higher; context, not design rainfall
- Attribution text shown in UI: "ERA5 reanalysis (Copernicus/ECMWF) via Open-Meteo.com"

### imd_thresholds — IMD daily rainfall intensity categories
- Provider / access: India Meteorological Department terminology (heavy 64.5–115.5, very heavy 115.6–204.4, extremely heavy ≥ 204.5 mm/day)   - Licence / terms: public classification, cite IMD   - Verified: no — confirm against IMD glossary PDF (Teammate C)
- data_status: curated   - Used by: P05 charts (reference lines), presets text
- Attribution text shown in UI: "Rainfall categories: India Meteorological Department"

### syn_rain — Hyperborea rainfall scenario presets
- Provider / access: ours, `config/scenarios.yaml` (moderate 15 mm/h × 3 h, heavy 40 × 2, extreme 80 × 2, record_day = ERA5 max day over 6 h)   - Licence: ours
- data_status: simulated (uniform design storms)   - Used by: P05 presets list, P08 cascade
- Quality / limitations: assumed intensities, no temporal/spatial pattern

### cop_dem — Copernicus DEM GLO-30 (30 m digital surface model)
- Provider / access: Microsoft Planetary Computer STAC, collection `cop-dem-glo-30` (`pipelines/fetch_dem.py`, pystac-client + planetary-computer signing)   - Licence / terms: Copernicus DEM licence — free use with attribution: "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved"   - Verified: no — confirm on the PC dataset page (Teammate C)
- Accessed: 2026-11-06   - Coverage: pilot + 2 km buffer, clipped → `local/rasters/dem.tif` (not committed)   - CRS / units: EPSG:4326, metres (EGM2008 heights)
- data_status: observed (but see limitations)   - Used by: P06 node elevations / drain slopes
- Quality / limitations: a surface model (includes buildings/trees), ~2–4 m vertical error; Salt Lake is ~3–6 m and flat, so DEM slopes are not reliable — drain slope is floored at 0.002 (planning §7) and flow direction only penalises uphill moves
- Attribution text shown in UI: "Copernicus DEM GLO-30 © DLR/Airbus, ESA"

### syn_drain — Hyperborea simulated stormwater network (drains, manholes, catchments)
- Provider / access: ours, `pipelines/build_drainage.py` (seed 42)   - Licence: ours (geometry derived from OSM roads, ODbL)   - Verified: n/a
- Accessed: 2026-11-06   - Coverage: 542 drains / 424 manholes / 540 catchments in the Sector V pilot   - CRS / units: EPSG:4326; m, m³/s
- data_status: **simulated** — NOT municipal records (D-09)   - Used by: P06 layers, P08 flood cascade
- Processing: one circular-equivalent drain per pilot road edge; diameter by road class (1.2 / 0.9 / 0.6 m); slope = max(DEM slope, 0.002); Manning full-flow n 0.015; condition factor U(0.6, 1.0); flow direction = elevation-penalised shortest path to an outfall (DAG); catchments = Voronoi of drain midpoints, runoff C area-weighted (roof 0.90 / road 0.85 / other 0.40)
- Quality / limitations: topology, sizes and condition are assumptions; DEM slopes unreliable on flat terrain (156/542 segments use the DEM slope, rest the 0.002 floor)
- Attribution text shown in UI: "SIMULATED NETWORK — not municipal records"

### cur_outfall — Hyperborea outfall placement
- Provider / access: ours, `pipelines/build_drainage.py`; rule confirmed by the user 2026-11-06   - Licence: ODbL-derived (OSM canals / water bodies)
- Coverage: 7 outfalls — 4 on Krishnapur Canal, 2 on unnamed canals at the wetland edge, 1 on Keshtopur Canal (water polygon, fallback rule)
- data_status: curated   - Used by: P06, P08
- Processing: manholes ≤ 80 m from an OSM canal line, ≥ 300 m apart, per connected component; components without a canal use an OSM pond/wetland/canal polygon ≤ 80 m
- Quality / limitations: no pumping-station or real outfall data yet (O-04, Teammate A); real Sector V discharge is pumped — not modelled

### cur_sites — Candidate development sites (S1–S3)
- Provider / access: ours, `pipelines/make_sites.py`; confirmed by the user 2026-11-06   - Licence: ODbL-derived (OSM land use, buildings, roads)
- Coverage: 3 × 40 × 40 m building-free plots in Sector V (S1 construction site, S2 industrial / flood-prone in the extreme preset, S3 commercial)
- data_status: curated   - Used by: P09 development assessment
- Quality / limitations: "vacant" inferred from OSM gaps — not a planning allocation; ownership, setbacks and FAR unknown

### norms — Development screening norms
- Provider / access: `config/norms.yaml` (floor height, occupant load, water lpcd, load density, diversity, runoff C, detention effect, check thresholds, weights)
- Sources: NBC 2016 Part 4 occupant loads; CPHEEO Manual on Water Supply & Treatment (1999) lpcd; others assumed — each value carries a note   - Verified: no — Teammate C to confirm NBC/CPHEEO figures
- data_status: curated (assumptions)   - Used by: P09

### syn_power — Hyperborea simulated electrical distribution network
- Provider / access: ours, `pipelines/build_power.py` (seed 42)   - Licence: ours (positions derived from OSM buildings/roads; substations from OSM, ODbL)   - Verified: n/a
- Accessed: 2026-11-06   - Coverage: 194 transformers (179 distribution 100–630 kVA, 15 dedicated HT 1–2.5 MVA), 8 schematic 11 kV feeders; substations Mahishbathan 33/11 kV (primary, 2 × 31.5 MVA assumed) ← Salt Lake grid (132/33 kV assumed), positions from OSM
- data_status: **simulated** (transformers, feeders) / curated (substation positions) — NOT the utility's grid (D-09)   - Used by: P10 cascade (transformer plinth 0.6 m → protective shutdown), P09 electrical check
- Processing: building load = BUA × W/m² (15 residential / 60 commercial by tag → OSM landuse → footprint rule) × diversity 0.6 / pf 0.9 (59.3 MVA total); k-means + bisection groups ≤ 504 kVA peak; rating = smallest standard ≥ 1.25 × peak; transformer on nearest road; facilities → nearest transformer
- Quality / limitations: no real feeder routes, ratings, loading or backup power; feeders are straight schematic lines
- Attribution text shown in UI: "SIMULATED NETWORK — not the actual utility grid"

### om_aq — Open-Meteo Air Quality API (CAMS)
- Provider / access: air-quality-api.open-meteo.com `/v1/air-quality` (no key), `backend/app/services/air.py`   - Licence / terms: CC BY 4.0; CAMS © ECMWF/Copernicus   - Verified: yes (open-meteo.com licence page, 2026-11-06)
- Accessed: live, cached 60 min (`local/cache/air.json`); fallback `data/snapshots/air.json`   - Coverage: model grid point near the pilot centroid (22.60 N, 88.40 E), hourly PM2.5 / PM10 / NO₂ / O₃, past 24 h + 72 h forecast   - CRS / units: WGS84; µg/m³
- data_status: modelled (CAMS global/regional model, ~10–40 km)   - Used by: P11 Environment panel
- Processing: 24-h means (O₃ max 8-h mean) → CPCB NAQI sub-indices (`config/naqi.yaml`) → category = max sub-index
- Quality / limitations: model, not CPCB station measurements; one value for the whole pilot
- Attribution text shown in UI: "Air quality: CAMS via Open-Meteo.com"

### naqi — India National Air Quality Index breakpoints (CPCB 2014)
- Provider / access: CPCB NAQI (CUPS/82/2014-15), transcribed in `config/naqi.yaml`   - Licence: public standard, cite CPCB   - Verified: no — Teammate C to confirm breakpoints
- data_status: curated   - Used by: P11 NAQI categories + colours

### esa_wc — ESA WorldCover 10 m v200 (2021)
- Provider / access: Microsoft Planetary Computer STAC `esa-worldcover` (asset `map`), `pipelines/landcover.py`   - Licence / terms: CC BY 4.0 — "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium"   - Verified: no — confirm on the PC dataset page (Teammate C)
- Accessed: 2026-11-06   - Coverage: pilot + 300 m, 10 m pixels   - CRS / units: EPSG:4326; class codes 10–100
- data_status: observed (classified from satellite imagery)   - Used by: P11 land-cover shares (pilot + per catchment), overlay PNG
- Quality / limitations: 2021 snapshot; ~75 % global accuracy; built-up dominates at 10 m in dense blocks
- Attribution text shown in UI: "© ESA WorldCover 2021 (CC BY 4.0)"

### s2_l2a — Sentinel-2 Level-2A surface reflectance
- Provider / access: Planetary Computer STAC `sentinel-2-l2a` (B04, B08, SCL), `pipelines/landcover.py`   - Licence / terms: Copernicus open data — "Contains modified Copernicus Sentinel data 2025–2026"   - Verified: yes (Copernicus data policy)
- Accessed: 2026-11-06   - Coverage: dry season 2025-12-01 → 2026-03-31, scenes with < 10 % cloud, pilot + 300 m   - CRS / units: native UTM 45N, resampled to the WorldCover grid; reflectance (BOA offset −1000 applied for baseline ≥ 04.00)
- data_status: observed (derived NDVI = (B08 − B04)/(B08 + B04), per-pixel median over scenes, SCL clouds/shadows masked)   - Used by: P11 NDVI overlay + per-catchment mean (P13 CV later)
- Attribution text shown in UI: "Contains modified Copernicus Sentinel data 2025–2026"

### syn_water — DEMO water-quality points
- Provider / access: ours, `pipelines/make_water_demo.py` (seed 7) → `data/synthetic/water_quality.geojson`   - Licence: ours
- Coverage: 8 points on OSM canals / water bodies (pH, turbidity NTU, TDS mg/L, sample dates Oct 2026)
- data_status: **simulated — DEMO DATA, not measurements** (no published values found, O-04)   - Used by: P11 water layer (points only, never interpolated)
- Attribution text shown in UI: "DEMO DATA — simulated water-quality values"

### cv_water — Surface water from Sentinel-2 NDWI (spectral index, not ML)
- Provider / access: ours, `pipelines/cv_water.py` on `s2_l2a` (B03, B08, SCL)   - Licence: method public (McFeeters 1996); data "Contains modified Copernicus Sentinel data 2025–2026"
- Coverage: pilot + 300 m; two seasons (dry Dec 2025–Mar 2026, post-monsoon Oct–Nov 2025), 5 scenes each, median NDWI > 0.1, polygons ≥ 400 m² → `data/processed/cv_water.gpkg`
- data_status: modelled (index-derived)   - Used by: P13 water layer (Environment); model card `models/model_cards/cv_water.md` (D-21)
- Quality / limitations: 10 m pixels, no monsoon (cloud) scenes, ≥ 99 % of area falls inside mapped OSM water (sanity check, not validation)

### ml_surrogate — Flood surrogate model output
- Provider / access: ours, `pipelines/train_surrogate.py` → `models/surrogate.joblib` (scikit-learn HistGradientBoosting, BSD-3 library; model MIT)
- Coverage: 542 simulated drains; trained on 2,000 Latin-hypercube runs of the P08 engine; held-out spatial blocks
- data_status: modelled (surrogate of a simulated rule engine — not validated on real events)   - Used by: P13 `/ml/quickscan`, Disaster Lab AI quick-scan; model card `models/model_cards/surrogate.md`

### P17 reuse note — global sources for Chennai + Pune
- Copernicus DEM (`cop_dem`), ERA5 (`om_archive`), Open-Meteo forecast (`om_forecast`) and CAMS (`om_aq`), ESA WorldCover (`esa_wc`), Sentinel-2 L2A (`s2_l2a`) are global: same providers, licences and processing, per-region bbox + timezone (Asia/Kolkata). IMD thresholds (`imd_thresholds`) and India NAQI (`naqi`) apply to both (India). Drainage, power, water-quality points stay **simulated** (`syn_drain`, `syn_power`, `syn_water`): no machine-readable municipal drain or utility data was found (Chennai GCC: ward PDF maps only; Pune PMC on OpenCity: two CSV tables (primary drain channels + coverage 2012, ward-wise road drain coverage 2016; public domain) with no geometry, so they cannot place drains) — checked 2026-11-07.
