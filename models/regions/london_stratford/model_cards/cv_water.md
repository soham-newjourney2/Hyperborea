# Model card — Hyperborea surface-water layer (`cv_water`)

**What it is:** a **spectral index, not machine learning** (decision D-21). Surface water is mapped with the McFeeters
NDWI = (Green − NIR) / (Green + NIR) on Sentinel-2 L2A (B03, B08), per-pixel median of low-cloud scenes, clouds and
shadows masked with the SCL band, water where NDWI > 0.1, polygons ≥ 400 m².
The planned pretrained CV model (NASA-IBM Prithvi-EO Sen1Floods11) was deferred: it needs a ~4–5 GB PyTorch/CUDA
stack; the planning cut order (§11) puts this NDWI fallback first. The layer and UI are ready for a model swap.

| | |
|---|---|
| Licence | Method: public (McFeeters 1996). Data: Copernicus Sentinel-2 — "Contains modified Copernicus Sentinel data 2025–2026" |
| Inputs | Sentinel-2 L2A B03, B08, SCL via Microsoft Planetary Computer |
| Hardware | CPU, offline |

## Output by season
| Season | Window | Scenes | Polygons | Water area (m²) | Inside mapped OSM water |
|---|---|---|---|---|---|
| summer | 2025-05-01/2025-09-30 | 5 | 0 | 0 | None % |
| winter | 2025-11-01/2026-03-31 | 5 | 1 | 1,200 | 0.0 % |

"Inside mapped OSM water" is a sanity check against OSM water bodies — not ground-truth validation.

## Limitations
- 10 m pixels: street waterlogging and narrow drains are invisible; mixed pixels at canal edges.
- Monsoon cloud cover: no usable scenes in Jun–Sep; flood-time water is not captured.
- Built-up surfaces and shadows can exceed the threshold (false positives); turbid water can fall below it.
- Not a validation of the flood engine.
