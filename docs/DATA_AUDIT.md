# Data audit — PASS

Generated 2026-11-11T18:01:11+00:00 by `scripts/audit_data.py` over every layer the API serves in 5 region(s) — sector_v, chennai_velachery, pune_kharadi, london_stratford, sydney_green_square (86 layers, 56,512 features). Status mix: observed 46,833, simulated 9,280, modelled 311, curated 88.

| Region · layer | Features | data_status | source_id | Result |
|---|---|---|---|---|
| sector_v · boundary | 1 | curated 1 | cur_boundary | PASS |
| sector_v · buildings | 1,510 | observed 1510 | osm | PASS |
| sector_v · roads | 6,298 | observed 6298 | osm | PASS |
| sector_v · facilities | 96 | observed 96 | osm | PASS |
| sector_v · waterways | 577 | observed 577 | osm | PASS |
| sector_v · water_quality | 8 | simulated 8 | syn_water | PASS |
| sector_v · cv_water | 32 | modelled 32 | cv_water | PASS |
| sector_v · drains | 542 | simulated 542 | syn_drain | PASS |
| sector_v · outfalls | 7 | curated 7 | cur_outfall | PASS |
| sector_v · catchments | 540 | simulated 540 | syn_drain | PASS |
| sector_v · drain_nodes | 424 | simulated 424 | syn_drain | PASS |
| sector_v · landuse | 259 | observed 259 | osm | PASS |
| sector_v · sites | 3 | curated 3 | cur_sites | PASS |
| sector_v · substations | 2 | curated 2 | osm | PASS |
| sector_v · transformers | 194 | simulated 194 | syn_power | PASS |
| sector_v · feeders | 8 | simulated 8 | syn_power | PASS |
| sector_v · osm_power | 20 | observed 20 | osm | PASS |
| chennai_velachery · boundary | 1 | curated 1 | cur_boundary | PASS |
| chennai_velachery · buildings | 4,748 | observed 4748 | osm | PASS |
| chennai_velachery · roads | 6,949 | observed 6949 | osm | PASS |
| chennai_velachery · facilities | 111 | observed 111 | osm | PASS |
| chennai_velachery · waterways | 120 | observed 120 | osm | PASS |
| chennai_velachery · water_quality | 8 | simulated 8 | syn_water | PASS |
| chennai_velachery · cv_water | 5 | modelled 5 | cv_water | PASS |
| chennai_velachery · sar_flood | 243 | modelled 243 | s1_rtc | PASS |
| chennai_velachery · drains | 1,055 | simulated 1055 | syn_drain | PASS |
| chennai_velachery · outfalls | 17 | curated 17 | cur_outfall | PASS |
| chennai_velachery · catchments | 1,052 | simulated 1052 | syn_drain | PASS |
| chennai_velachery · drain_nodes | 874 | simulated 874 | syn_drain | PASS |
| chennai_velachery · landuse | 115 | observed 115 | osm | PASS |
| chennai_velachery · sites | 3 | curated 3 | cur_sites | PASS |
| chennai_velachery · substations | 2 | curated 2 | osm | PASS |
| chennai_velachery · transformers | 183 | simulated 183 | syn_power | PASS |
| chennai_velachery · feeders | 8 | simulated 8 | syn_power | PASS |
| chennai_velachery · osm_power | 57 | observed 57 | osm | PASS |
| pune_kharadi · boundary | 1 | curated 1 | cur_boundary | PASS |
| pune_kharadi · buildings | 1,883 | observed 1883 | osm | PASS |
| pune_kharadi · roads | 4,120 | observed 4120 | osm | PASS |
| pune_kharadi · facilities | 62 | observed 62 | osm | PASS |
| pune_kharadi · waterways | 23 | observed 23 | osm | PASS |
| pune_kharadi · water_quality | 3 | simulated 3 | syn_water | PASS |
| pune_kharadi · cv_water | 11 | modelled 11 | cv_water | PASS |
| pune_kharadi · drains | 608 | simulated 608 | syn_drain | PASS |
| pune_kharadi · outfalls | 12 | curated 12 | cur_outfall | PASS |
| pune_kharadi · catchments | 607 | simulated 607 | syn_drain | PASS |
| pune_kharadi · drain_nodes | 495 | simulated 495 | syn_drain | PASS |
| pune_kharadi · landuse | 122 | observed 122 | osm | PASS |
| pune_kharadi · sites | 3 | curated 3 | cur_sites | PASS |
| pune_kharadi · substations | 1 | curated 1 | osm | PASS |
| pune_kharadi · transformers | 137 | simulated 137 | syn_power | PASS |
| pune_kharadi · feeders | 2 | simulated 2 | syn_power | PASS |
| pune_kharadi · osm_power | 19 | observed 19 | osm | PASS |
| london_stratford · boundary | 1 | curated 1 | cur_boundary | PASS |
| london_stratford · buildings | 1,348 | observed 1348 | osm | PASS |
| london_stratford · roads | 4,686 | observed 4686 | osm | PASS |
| london_stratford · facilities | 195 | observed 195 | osm | PASS |
| london_stratford · waterways | 311 | observed 311 | osm | PASS |
| london_stratford · water_quality | 8 | simulated 8 | syn_water | PASS |
| london_stratford · cv_water | 1 | modelled 1 | cv_water | PASS |
| london_stratford · drains | 332 | simulated 332 | syn_drain | PASS |
| london_stratford · outfalls | 15 | curated 15 | cur_outfall | PASS |
| london_stratford · catchments | 332 | simulated 332 | syn_drain | PASS |
| london_stratford · drain_nodes | 262 | simulated 262 | syn_drain | PASS |
| london_stratford · landuse | 3,875 | observed 3875 | osm | PASS |
| london_stratford · sites | 3 | curated 3 | cur_sites | PASS |
| london_stratford · substations | 2 | curated 2 | osm | PASS |
| london_stratford · transformers | 139 | simulated 139 | syn_power | PASS |
| london_stratford · feeders | 8 | simulated 8 | syn_power | PASS |
| london_stratford · osm_power | 1,371 | observed 1371 | osm | PASS |
| sydney_green_square · boundary | 1 | curated 1 | cur_boundary | PASS |
| sydney_green_square · buildings | 1,318 | observed 1318 | osm | PASS |
| sydney_green_square · roads | 3,908 | observed 3908 | osm | PASS |
| sydney_green_square · facilities | 104 | observed 104 | osm | PASS |
| sydney_green_square · waterways | 160 | observed 160 | osm | PASS |
| sydney_green_square · water_quality | 8 | simulated 8 | syn_water | PASS |
| sydney_green_square · cv_water | 19 | modelled 19 | cv_water | PASS |
| sydney_green_square · drains | 405 | simulated 405 | syn_drain | PASS |
| sydney_green_square · outfalls | 8 | curated 8 | cur_outfall | PASS |
| sydney_green_square · catchments | 403 | simulated 403 | syn_drain | PASS |
| sydney_green_square · drain_nodes | 292 | simulated 292 | syn_drain | PASS |
| sydney_green_square · landuse | 1,311 | observed 1311 | osm | PASS |
| sydney_green_square · sites | 3 | curated 3 | cur_sites | PASS |
| sydney_green_square · substations | 2 | curated 2 | osm | PASS |
| sydney_green_square · transformers | 335 | simulated 335 | syn_power | PASS |
| sydney_green_square · feeders | 8 | simulated 8 | syn_power | PASS |
| sydney_green_square · osm_power | 1,157 | observed 1157 | osm | PASS |

## Repository checks
- `.env` tracked: no
- Files in Git LFS: 62
- Non-LFS files > 5 MB: none
- Possible secrets in tracked text files: none

## Rules checked
- Every feature has `asset_id` (unique within and across layers), a valid `data_status`, and a `source_id` registered in `docs/DATA_SOURCES.md`.
- Layers that must be labelled simulated: catchments, drain_nodes, drains, feeders, transformers, water_quality.
- Every simulated or modelled feature states its assumptions.
