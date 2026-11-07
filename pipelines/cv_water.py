"""P13 A (fallback, D-21): surface water from Sentinel-2 NDWI — a SPECTRAL INDEX, NOT ML.

McFeeters NDWI = (B03 − B08) / (B03 + B08), per-pixel median over low-cloud scenes, two seasons (dry + post-monsoon),
SCL-masked; water = NDWI > threshold; polygons ≥ min area → data/processed/cv_water.gpkg layer `cv_water`.
Checked against mapped OSM water. Run after landcover:  python -m pipelines.cv_water
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import geopandas as gpd
import numpy as np
import planetary_computer
import pystac_client
import rioxarray  # noqa: F401
import xarray as xr
from rasterio.enums import Resampling
from rasterio.features import shapes
from shapely.geometry import shape

from pipelines.osm_common import ROOT

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
UTM = 32645
BUFFER_M = 300
THRESHOLD = 0.1          # urban McFeeters threshold (0 is the textbook value; 0.1 cuts built-up false positives)
MIN_AREA_M2 = 400        # ≥ 4 pixels at 10 m
MAX_SCENES = 5
SEASONS = {"dry": "2025-12-01/2026-03-31", "post_monsoon": "2025-10-01/2025-11-30"}
SCL_BAD = {0, 1, 3, 8, 9, 10, 11}
OUT = ROOT / "data" / "processed" / "cv_water.gpkg"
CARD = ROOT / "models" / "model_cards" / "cv_water.md"


def season_ndwi(cat, bbox_utm, window: str):
    w, s, e, n = gpd.GeoSeries.from_xy(bbox_utm[[0, 2]], bbox_utm[[1, 3]], crs=UTM).to_crs(4326).total_bounds
    items = sorted(cat.search(collections=["sentinel-2-l2a"], bbox=[w, s, e, n], datetime=window,
                              query={"eo:cloud_cover": {"lt": 15}}).items(),
                   key=lambda i: i.properties["eo:cloud_cover"])[:MAX_SCENES]
    stack, used, ref = [], [], None
    for it in items:
        rd = lambda b: xr.open_dataarray(it.assets[b].href, engine="rasterio").squeeze(drop=True).rio.clip_box(*bbox_utm)  # noqa: E731
        g, nir = rd("B03").astype("float32"), rd("B08").astype("float32")
        ref = g if ref is None else ref
        g, nir = g.rio.reproject_match(ref), nir.rio.reproject_match(ref)
        scl = rd("SCL").rio.reproject_match(ref, resampling=Resampling.nearest)
        off = 1000 if float(str(it.properties.get("s2:processing_baseline", "0")) or 0) >= 4 else 0
        rg, rn = (g - off) / 10000, (nir - off) / 10000
        nd = ((rg - rn) / (rg + rn)).where(~scl.isin(list(SCL_BAD)) & (rg + rn > 0))
        stack.append(nd.values)
        used.append({"id": it.id, "date": it.datetime.date().isoformat(), "cloud_pct": it.properties["eo:cloud_cover"]})
    if not stack:
        return None, [], None
    return np.nanmedian(np.stack(stack), axis=0), used, ref


def main() -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    g = ROOT / "data" / "processed" / "hyperborea.gpkg"
    bnd = gpd.read_file(g, layer="boundary").to_crs(UTM)
    area = bnd.buffer(BUFFER_M).iloc[0]
    bbox = np.array(area.bounds)
    osm_water = gpd.read_file(g, layer="waterways").to_crs(UTM)
    osm_water = osm_water[osm_water.geom_type.str.contains("Polygon")].geometry.union_all()
    cat = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)
    rows, geoms, summary = [], [], {}
    for season, window in SEASONS.items():
        ndwi, used, ref = season_ndwi(cat, bbox, window)
        if ndwi is None:
            summary[season] = {"window": window, "scenes": [], "note": "no low-cloud scenes"}
            continue
        mask = (np.nan_to_num(ndwi, nan=-1) > THRESHOLD).astype(np.uint8)
        polys = []
        for geom, val in shapes(mask, mask=mask.astype(bool), transform=ref.rio.transform()):
            p = shape(geom).intersection(area)
            if not p.is_empty and p.area >= MIN_AREA_M2:
                polys.append(p)
        total = sum(p.area for p in polys)
        in_osm = sum(p.intersection(osm_water).area for p in polys)
        summary[season] = {"window": window, "scenes": used, "polygons": len(polys), "water_area_m2": round(total),
                           "share_inside_osm_water_pct": round(100 * in_osm / total, 1) if total else None}
        for k, p in enumerate(polys, 1):
            rows.append({"asset_id": f"cvw_{season}_{k:03d}", "asset_type": "surface_water", "name": None,
                         "data_status": "modelled", "source_id": "cv_water", "observed_at": used[0]["date"],
                         "ingested_at": now, "confidence": "med" if p.intersects(osm_water) else "low",
                         "assumptions": f"SPECTRAL INDEX — not ML: McFeeters NDWI > {THRESHOLD} on the per-pixel median of "
                                        f"{len(used)} Sentinel-2 L2A scenes ({window}); 10 m pixels cannot see street waterlogging",
                         "attrs": json.dumps({"season": season, "area_m2": round(p.area, 1),
                                              "overlaps_osm_water": bool(p.intersects(osm_water)), "method": "ndwi_mcfeeters",
                                              "threshold": THRESHOLD, "scenes": [u["date"] for u in used]}),
                         "in_pilot": bool(p.representative_point().within(bnd.geometry.iloc[0]))})
            geoms.append(p)
    gdf = gpd.GeoDataFrame(rows, geometry=geoms, crs=UTM).to_crs(4326)
    OUT.unlink(missing_ok=True)
    gdf.to_file(OUT, layer="cv_water", driver="GPKG", layer_options={"SPATIAL_INDEX": "NO"})
    (ROOT / "data" / "processed" / "cv_water_summary.json").write_text(json.dumps({
        "method": "NDWI (McFeeters 1996) threshold — spectral index, not machine learning (D-21)",
        "threshold": THRESHOLD, "min_area_m2": MIN_AREA_M2, "seasons": summary, "generated_at": now}, indent=1), encoding="utf-8")
    write_card(summary)
    for s, v in summary.items():
        print(s, {k: v.get(k) for k in ("polygons", "water_area_m2", "share_inside_osm_water_pct")}, [u["date"] for u in v.get("scenes", [])])
    print(f"wrote {len(gdf)} polygons → {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.2f} MB)")


def write_card(summary: dict) -> None:
    rows = "\n".join(f"| {s} | {v['window']} | {len(v.get('scenes', []))} | {v.get('polygons', 0)} | "
                     f"{v.get('water_area_m2', 0):,} | {v.get('share_inside_osm_water_pct')} % |" for s, v in summary.items())
    CARD.parent.mkdir(parents=True, exist_ok=True)
    CARD.write_text(f"""# Model card — Hyperborea surface-water layer (`cv_water`)

**What it is:** a **spectral index, not machine learning** (decision D-21). Surface water is mapped with the McFeeters
NDWI = (Green − NIR) / (Green + NIR) on Sentinel-2 L2A (B03, B08), per-pixel median of low-cloud scenes, clouds and
shadows masked with the SCL band, water where NDWI > {THRESHOLD}, polygons ≥ {MIN_AREA_M2} m².
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
{rows}

"Inside mapped OSM water" is a sanity check against OSM water bodies — not ground-truth validation.

## Limitations
- 10 m pixels: street waterlogging and narrow drains are invisible; mixed pixels at canal edges.
- Monsoon cloud cover: no usable scenes in Jun–Sep; flood-time water is not captured.
- Built-up surfaces and shadows can exceed the threshold (false positives); turbid water can fall below it.
- Not a validation of the flood engine.
""", encoding="utf-8")


if __name__ == "__main__":
    main()
