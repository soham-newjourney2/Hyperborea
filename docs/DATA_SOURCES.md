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

### cur_boundary — Hyperborea pilot boundary (Salt Lake Sector V)
- Provider / access: ours — `pipelines/scan_candidates.py` + `pipelines/make_boundary.py`   - Licence / terms: ODbL-derived (built from OSM)   - Verified: n/a
- Accessed: 2026-11-06   - Coverage: 2.83 km², one polygon   - CRS / units: EPSG:4326
- data_status: curated   - Used by: P02 onward (D-17)
- Processing: polygonize OSM roads in the Bidhannagar ∩ study window → assign each cell to the nearest `"XX Block"` place label (≤ 450 m) → dissolve Sector V blocks (AN AP AQ BN CN CP DN DP EM EN GN GP HM) → drop slivers < 2 % of largest part
- Quality / limitations: not an official municipal boundary; edges follow roads, block membership from the Salt Lake block grid
- Attribution text shown in UI: "Pilot boundary: Hyperborea (derived from © OpenStreetMap contributors)"

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
