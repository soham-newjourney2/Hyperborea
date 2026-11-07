# Data audit — PASS

Generated 2026-11-07T12:28:04+00:00 by `scripts/audit_data.py` over every layer the API serves (17 layers, 10,521 features). Status mix: observed 8,760, simulated 1,716, modelled 32, curated 13.

| Layer | Features | data_status | source_id | Result |
|---|---|---|---|---|
| boundary | 1 | curated 1 | cur_boundary | PASS |
| buildings | 1,510 | observed 1510 | osm | PASS |
| roads | 6,298 | observed 6298 | osm | PASS |
| facilities | 96 | observed 96 | osm | PASS |
| waterways | 577 | observed 577 | osm | PASS |
| water_quality | 8 | simulated 8 | syn_water | PASS |
| cv_water | 32 | modelled 32 | cv_water | PASS |
| drains | 542 | simulated 542 | syn_drain | PASS |
| outfalls | 7 | curated 7 | cur_outfall | PASS |
| catchments | 540 | simulated 540 | syn_drain | PASS |
| drain_nodes | 424 | simulated 424 | syn_drain | PASS |
| landuse | 259 | observed 259 | osm | PASS |
| sites | 3 | curated 3 | cur_sites | PASS |
| substations | 2 | curated 2 | osm | PASS |
| transformers | 194 | simulated 194 | syn_power | PASS |
| feeders | 8 | simulated 8 | syn_power | PASS |
| osm_power | 20 | observed 20 | osm | PASS |

## Repository checks
- `.env` tracked: no
- Local-only (Claude Code) files tracked: no
- Committed data/model files > 5 MB: none
- Possible secrets in tracked text files: none

## Rules checked
- Every feature has `asset_id` (unique within and across layers), a valid `data_status`, and a `source_id` registered in `docs/DATA_SOURCES.md`.
- Layers that must be labelled simulated: catchments, drain_nodes, drains, feeders, transformers, water_quality.
- Every simulated or modelled feature states its assumptions.
