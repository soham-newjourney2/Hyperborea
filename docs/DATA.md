# Data

Everything the app shows comes from the files described here. Each feature carries **provenance** so nothing simulated
or modelled is ever presented as observed.

## Folder layout (one folder per region)
```
data/regions/<id>/raw/osm/<UTC stamp>/   OSM clip as fetched (immutable; features.osm, drive/walk graphs, layer GPKGs, meta.json)
data/regions/<id>/processed/             what the API serves: hyperborea.gpkg (base layers), drainage.gpkg, power.gpkg,
                                         cv_water.gpkg, sar_flood.gpkg*, drive_graph.json, climate_{daily.csv,summary.json},
                                         landcover_stats.json, cv_water_summary.json, validation.json*
data/regions/<id>/curated/               boundary.geojson, sites.geojson (+ candidates.geojson for Sector V)
data/regions/<id>/synthetic/             water_quality.geojson (DEMO points)
data/regions/<id>/snapshots/             backend fallbacks (weather, air) + frozen demo results (flood heavy/extreme, dev compare)
models/regions/<id>/                     surrogate.joblib, surrogate_metrics.json, model_cards/
local/regions/<id>/osm · rasters          Geofabrik/BBBike extract, DEM GeoTIFF (Git LFS)
frontend/public/snapshots/regions/<id>/   offline copies of API responses; overlays/regions/<id>/ WorldCover + NDVI PNGs
```
`*` Chennai only. Region ids: `sector_v`, `chennai_velachery`, `pune_kharadi`, `london_stratford`, `sydney_green_square`.
Files over 5 MB (OSM extracts, rasters, raw OSM, two large GeoPackages) are stored with **Git LFS**.

## Provenance model
Every feature has: `asset_id` (stable, e.g. `bld_osm_w123`, `drn_syn_…`) · `asset_type` · `name` ·
**`data_status`** (`observed` · `curated` · `modelled` · `simulated` · `unknown`) · **`source_id`** (an entry below) ·
`observed_at` · `ingested_at` · `confidence` · `assumptions` · `attrs` (type-specific values).
Every relationship edge has a `type`, the `rule` that created it, `data_status` and `confidence`.
`python scripts/audit_data.py` fails if any feature lacks these, uses an unregistered `source_id`, or if a simulated layer
is not labelled simulated.

| data_status | Meaning | Examples |
|---|---|---|
| observed | measured / mapped by someone else | OSM buildings and roads, LiDAR terrain, WorldCover |
| curated | chosen or assembled by the team from observed data | pilot boundaries, outfall placement, candidate sites |
| modelled | computed by a model from observations | weather forecast, ERA5, CAMS air quality, NDWI water, radar flood mask, surrogate output |
| simulated | invented to fill a gap — never presented as real | drain network, transformers and feeders, water-quality demo points, rainfall presets |

## What is real and what is simulated, per pilot
| Pilot | Area | Buildings · roads · facilities (OSM) | Terrain | Drains / power | Air index | Extra real data |
|---|---|---|---|---|---|---|
| Kolkata · Salt Lake Sector V | 2.83 km² | 1,510 · 542 · 96 | Copernicus DEM 30 m | simulated (542 drains, 194 transformers) | India NAQI | — |
| Chennai · Velachery | 3.07 km² | 4,748 · 1,055 · 111 | Copernicus DEM 30 m | simulated (1,055 / 183) | India NAQI | Sentinel-1 flood map, Dec 2015 (validation) |
| Pune · Kharadi | 3.18 km² | 1,883 · 608 · 62 | Copernicus DEM 30 m | simulated (608 / 137) | India NAQI | — |
| London · Hackney Wick & Stratford | 2.90 km² | 1,348 · 332 · 195 | **EA LiDAR DTM 5 m** | simulated (332 / 139) | UK DAQI | — |
| Sydney · Green Square & Alexandria | 3.12 km² | 1,318 · 405 · 104 | Copernicus DEM 30 m | simulated (405 / 335) | NSW AQC | — |

Facilities include a 2 km buffer around the pilot. Boundaries are curated study areas, not official wards (Sector V
follows the Salt Lake block grid; the others are rectangles). No machine-readable municipal drain or utility network was
found for any pilot: Chennai publishes ward PDF maps only; Pune's drain tables have no geometry; UK Power Networks'
substation data needs a registered account; City of Sydney's drainage listing has no data; Ausgrid publishes substation
loads but no locations.

## Sources
Licences were checked on the provider pages on the dates given.

### osm — OpenStreetMap
- **What:** buildings, drive/walk roads, amenities (hospitals, clinics, schools, colleges, fire, police, stations), power, waterways, land use.
- **Access:** Geofabrik extracts — India eastern-zone (Kolkata), southern-zone (Chennai), western-zone (Pune), England greater-london (London); BBBike city extract (Sydney). Clipped to pilot + 2 km with pyosmium (`pipelines/osm_pbf.py`); OSM timestamp from the extract header in `raw/osm/<stamp>/meta.json`.
- **Licence:** ODbL 1.0 — "© OpenStreetMap contributors". Accessed 2026-11-06 → 2026-11-11.
- **Status:** observed. Building height is `observed` (height tag), `modelled` (levels × 3.2 m) or `assumed` (9 m), stated per building.
- **Limits:** few buildings carry height tags; footprints incomplete in informal areas; no drainage or power topology.

### cur_boundary — Pilot boundaries
- Ours. Sector V: OSM road cells assigned to Salt Lake block labels (`scan_candidates.py`, `make_boundary.py`). Other pilots: study rectangles from `config/regions.yaml` (`make_region_boundary.py`). **curated**, not official boundaries.

### cop_dem — Copernicus DEM GLO-30
- Planetary Computer STAC `cop-dem-glo-30`. "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA". **observed** surface model (includes roofs/trees, ~2–4 m vertical error) → ground proxy = 3×3 minimum; drain slope floored at 0.002. Kolkata, Chennai, Pune, Sydney.

### ea_lidar_dtm — Environment Agency LIDAR Composite DTM 2022 (England)
- Defra WCS 2.0.1, coverage `…Lidar_Composite_Elevation_DTM_1m`, requested in 1.5 km tiles, server-resampled to 5 m, EPSG:27700 → 4326. Open Government Licence v3.0 — "© Environment Agency copyright and/or database right 2022". **observed** bare-earth terrain (±15 cm RMSE). London only.

### om_forecast — Open-Meteo forecast
- `api.open-meteo.com/v1/forecast`, pilot centroid, current + 72 h hourly, region timezone; cached 30 min with snapshot fallback. CC BY 4.0 — "Weather data by Open-Meteo.com". **modelled** (forecast, not observation). Drives the early warning.

### om_archive — ERA5 reanalysis via Open-Meteo
- Daily (and, for validation, hourly) ERA5 for the pilot's grid cell, 1981 → today → annual totals, wettest day, heavy-rain days, trends. CC BY 4.0; ERA5 © ECMWF / Copernicus. **modelled** — a ~25 km cell smooths local cloudbursts (e.g. London's record day is 34.2 mm).

### imd_thresholds — IMD rainfall categories (India pilots)
- Heavy 64.5–115.5, very heavy 115.6–204.4, extremely heavy ≥ 204.5 mm/day, India Meteorological Department. **curated**.

### etccdi_thresholds — ETCCDI-style thresholds (London, Sydney)
- 20 / 30 / 50 mm/day following the WMO ETCCDI extreme-precipitation indices. **curated**; labelled "not an official UK / BoM category".

### syn_rain — Rainfall scenario presets
- `config/scenarios.yaml`: moderate 15 mm/h × 3 h, design 20 × 2, heavy 40 × 2, extreme 80 × 2, record day = ERA5 wettest day over 6 h. **simulated** uniform design storms.

### syn_drain — Simulated stormwater network
- Ours (`build_drainage.py`, seed 42): one drain per pilot road edge, diameter = smallest standard pipe carrying the region's design storm (20 mm/h India, 30 London, 40 Sydney — assumed) and never below the road-class minimum; Manning full flow (n 0.015); condition factor U(0.6, 1.0); flow direction = elevation-penalised path to an outfall; Voronoi catchments with area-weighted runoff C. **simulated — not municipal records.**

### cur_outfall — Outfall placement
- Ours: manholes ≤ 80 m from an OSM canal, ≥ 300 m apart, per connected network; otherwise a pond / wetland / canal polygon. **curated**. No pumping stations modelled.

### syn_power — Simulated electrical network
- Ours (`build_power.py`, seed 42): building load = floor area × W/m² (15 residential / 60 commercial) × diversity 0.6; buildings grouped into distribution transformers (100–630 kVA) or dedicated HT units; schematic 11 kV feeders from the nearest OSM substation. **simulated — not the utility grid**; substation positions from OSM (curated).

### cur_sites — Candidate development sites
- Ours (`make_sites.py`): 40 × 40 m (or 30 × 30 m) building-free plots — S1 dry, S2 flood-prone, S3 central. **curated**; "vacant" inferred from OSM gaps, not a planning allocation.

### norms — Development screening norms
- `config/norms.yaml`: NBC 2016 occupant loads, CPHEEO water demand, assumed load densities and thresholds. **curated** (Indian defaults, also used for London and Sydney — stated in results).

### om_aq — Air quality (CAMS via Open-Meteo)
- `air-quality-api.open-meteo.com`, hourly PM2.5, PM10, NO₂, O₃ near the pilot centroid. CC BY 4.0; CAMS © ECMWF / Copernicus. **modelled**, one value per pilot, not station data. Converted to the local index below.

### naqi — India National Air Quality Index (CPCB 2014)
- `config/naqi.yaml`. PM / NO₂ 24-h mean, O₃ max 8-h mean; index = worst sub-index. **curated**.

### daqi — UK Daily Air Quality Index (Defra / COMEAP)
- `config/daqi.yaml` from GOV.UK (Open Government Licence v3.0). PM 24-h mean, NO₂ worst hour, O₃ max 8-h mean → levels 1–10. **curated**.

### nsw_aqc — NSW Air Quality Categories
- `config/nsw_aqc.yaml`: bands 0.67 / 1 / 1.5 / 2 × national standard (PM2.5 25, PM10 50 µg/m³; O₃ 10, NO₂ 8 pphm, converted at 25 °C). **curated**; intermediate NO₂ bands inferred from that pattern.

### esa_wc — ESA WorldCover 10 m (2021)
- Planetary Computer `esa-worldcover`. CC BY 4.0 — "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021)". **observed** classification; land-cover shares per pilot and catchment.

### s2_l2a — Sentinel-2 Level-2A
- Planetary Computer `sentinel-2-l2a` (B03, B04, B08, SCL), dry/low-cloud windows per region. "Contains modified Copernicus Sentinel data 2025–2026". NDVI overlay and the NDWI water layer.

### cv_water — Surface water (NDWI)
- Ours (`cv_water.py`): median NDWI > 0.1 over two seasons, polygons ≥ 400 m². **modelled** spectral index — **not machine learning**. Narrow canals (< 10 m) are missed.

### s1_rtc — Sentinel-1 RTC radar (validation)
- Planetary Computer `sentinel-1-rtc`, VV, orbit 92 descending. CC BY 4.0 + Copernicus terms. Chennai: dry references 2015-03-05, 2015-05-28, 2016-02-28; post-flood 2015-12-06; control 2015-12-18. Flood = open-water darkening (> 3 dB, < −15 dB) or urban brightening near buildings (> 3 dB, double bounce; lower confidence). **modelled** from observation (`validate_flood.py` → `sar_flood.gpkg`, `validation.json`).
- No pass exists over Chennai between 2023-11-18 and 2024-01-17, so Cyclone Michaung (Dec 2023) could not be used.

### wwa_chennai_2015 — Chennai station rainfall, 1–2 Dec 2015
- World Weather Attribution event analysis: mean of station 24-h totals = **286 mm** (max 494 mm). **observed** (cited summary). Used as validation rain input; ERA5 gave only 119 mm over three days.

### syn_water — Water-quality points
- Ours (`make_water_demo.py`): pH, turbidity, TDS at points on OSM canals / water bodies. **simulated — DEMO DATA, not measurements.**

### ml_surrogate — Flood surrogate model
- Ours (`train_surrogate.py`): scikit-learn HistGradientBoosting per region, trained on 2,000 engine runs, tested on held-out spatial blocks (F1 0.86–0.93 vs 0.37–0.58 for a rain-threshold baseline). **modelled** — a copy of our engine, not validated on real floods. Model cards in `models/regions/<id>/model_cards/`.

## Attribution (shown in the app footer and reports)
© OpenStreetMap contributors (ODbL) · Copernicus DEM GLO-30 © DLR/Airbus, ESA · © Environment Agency 2022 (OGL v3, London
terrain) · ERA5 (Copernicus/ECMWF), weather and CAMS air quality via Open-Meteo.com (CC BY 4.0) · © ESA WorldCover 2021
(CC BY 4.0) · Contains modified Copernicus Sentinel data 2015–2026 · Sentinel-2 cloudless by EOX (base imagery).
