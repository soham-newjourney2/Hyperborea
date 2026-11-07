"""P11: ESA WorldCover 2021 class shares + Sentinel-2 dry-season NDVI for the pilot and each catchment.

Out: data/processed/landcover_stats.json, frontend/public/overlays/{worldcover,ndvi}.png (EPSG:4326, bounds in stats).
Run after build_drainage:  python -m pipelines.landcover
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import geopandas as gpd
import matplotlib
import numpy as np
import planetary_computer
import pystac_client
import rioxarray  # noqa: F401
import xarray as xr
from PIL import Image
from rasterio.enums import Resampling
from rasterio.features import rasterize

from pipelines.osm_common import ROOT
from backend.app.core import regions as R  # noqa: E402  (P16: HYPERBOREA_REGION → paths, CRS, timezone)

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
BUFFER_M = 300
OUT_JSON = R.data_dir("processed") / "landcover_stats.json"
OVERLAY_REL = "overlays" if R.current() == R.DEFAULT else f"overlays/regions/{R.current()}"  # P17: per-region PNGs
OVERLAYS = ROOT / "frontend" / "public" / OVERLAY_REL
WC_CLASSES = {  # code: (label, official colour)
    10: ("Tree cover", "#006400"), 20: ("Shrubland", "#ffbb22"), 30: ("Grassland", "#ffff4c"),
    40: ("Cropland", "#f096ff"), 50: ("Built-up", "#fa0000"), 60: ("Bare / sparse", "#b4b4b4"),
    70: ("Snow / ice", "#f0f0f0"), 80: ("Permanent water", "#0064c8"), 90: ("Herbaceous wetland", "#0096a0"),
    95: ("Mangroves", "#00cf75"), 100: ("Moss / lichen", "#fae6a0"),
}
GREEN = {10, 20, 30, 40, 90, 95}
S2_WINDOW = R.cfg().get("s2_window", "2025-12-01/2026-03-31")  # latest complete dry season (low cloud)
MAX_SCENES = 6
SCL_BAD = {0, 1, 3, 8, 9, 10, 11}  # no data, saturated, cloud shadow, cloud med/high, cirrus, snow


def rgba(img_rgb: np.ndarray, alpha: np.ndarray, path):
    OVERLAYS.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.dstack([img_rgb, alpha]).astype(np.uint8), "RGBA").save(path, optimize=True)


def hex2rgb(h: str) -> tuple[int, int, int]:
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def main() -> None:
    g = R.data_dir("processed") / "hyperborea.gpkg"
    bnd = gpd.read_file(g, layer="boundary")
    cats = gpd.read_file(R.data_dir("processed") / "drainage.gpkg", layer="catchments")
    area = bnd.to_crs(R.metric_crs()).buffer(BUFFER_M).to_crs(4326)
    w, s, e, n = area.total_bounds
    cat = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)

    # ---- WorldCover 2021 ----
    wc_items = [i for i in cat.search(collections=["esa-worldcover"], bbox=[w, s, e, n]).items()
                if str(i.properties.get("start_datetime", i.datetime))[:4] == "2021" or "2021" in i.id]
    if not wc_items:
        raise SystemExit("WorldCover 2021 item not found")
    wc = xr.open_dataarray(wc_items[0].assets["map"].href, engine="rasterio").squeeze(drop=True).rio.clip_box(w, s, e, n)
    arr = wc.values.astype(np.int16)
    transform, shape = wc.rio.transform(), arr.shape
    in_pilot = rasterize([(bnd.geometry.iloc[0], 1)], out_shape=shape, transform=transform, fill=0).astype(bool)
    vals, counts = np.unique(arr[in_pilot], return_counts=True)
    pilot = {WC_CLASSES[v][0]: round(100 * c / in_pilot.sum(), 2) for v, c in zip(vals, counts) if v in WC_CLASSES}
    cat_idx = rasterize([(geom, i + 1) for i, geom in enumerate(cats.geometry)], out_shape=shape, transform=transform,
                        fill=0)
    per = {}
    for i, cid in enumerate(cats.asset_id, 1):
        m = cat_idx == i
        if not m.any():
            continue
        v, c = np.unique(arr[m], return_counts=True)
        sh = dict(zip(v.tolist(), (100 * c / m.sum()).tolist()))
        per[cid] = {"built_up_pct": round(sh.get(50, 0.0), 1),
                    "green_pct": round(sum(p for k, p in sh.items() if k in GREEN), 1),
                    "water_pct": round(sh.get(80, 0.0), 1), "pixels": int(m.sum())}
    lut = np.zeros((256, 3), np.uint8)
    for code, (_, col) in WC_CLASSES.items():
        lut[code] = hex2rgb(col)
    rgba(lut[arr.clip(0, 255)], np.where(arr > 0, np.where(in_pilot, 190, 90), 0), OVERLAYS / "worldcover.png")
    b4326 = [round(float(x), 6) for x in wc.rio.bounds()]

    # ---- Sentinel-2 dry-season NDVI (median of low-cloud scenes, SCL-masked) ----
    items = sorted(cat.search(collections=["sentinel-2-l2a"], bbox=[w, s, e, n], datetime=S2_WINDOW,
                              query={"eo:cloud_cover": {"lt": 10}}).items(),
                   key=lambda i: i.properties["eo:cloud_cover"])[:MAX_SCENES]
    stack, used = [], []
    for it in items:
        epsg = it.properties.get("proj:epsg") or R.metric_crs()
        box = gpd.GeoSeries.from_xy([w, e], [s, n], crs=4326).to_crs(epsg).total_bounds
        rd = lambda b: xr.open_dataarray(it.assets[b].href, engine="rasterio").squeeze(drop=True).rio.clip_box(*box)  # noqa: E731
        b4, b8 = rd("B04").astype("float32"), rd("B08").astype("float32")
        scl = rd("SCL").rio.reproject_match(b4, resampling=Resampling.nearest)
        off = 1000 if float(str(it.properties.get("s2:processing_baseline", "0")).replace("N", "") or 0) >= 4 else 0
        r4, r8 = (b4 - off) / 10000, (b8 - off) / 10000
        nd = ((r8 - r4) / (r8 + r4)).where(~scl.isin(list(SCL_BAD)) & (r8 + r4 > 0))
        nd = nd.rio.write_crs(epsg).rio.reproject_match(wc, resampling=Resampling.bilinear)
        stack.append(nd.values)
        used.append({"id": it.id, "date": it.datetime.date().isoformat(), "cloud_pct": it.properties["eo:cloud_cover"]})
    if not stack:
        raise SystemExit("no Sentinel-2 scenes found")
    ndvi = np.nanmedian(np.stack(stack), axis=0)
    ndvi_pilot = float(np.nanmean(ndvi[in_pilot]))
    for i, cid in enumerate(cats.asset_id, 1):
        m = (cat_idx == i) & np.isfinite(ndvi)
        if cid in per and m.any():
            per[cid]["ndvi_mean"] = round(float(ndvi[m].mean()), 3)
    cmap = matplotlib.colormaps["RdYlGn"]
    norm = np.clip((ndvi + 0.1) / 0.9, 0, 1)
    rgb = (cmap(np.nan_to_num(norm))[..., :3] * 255).astype(np.uint8)
    rgba(rgb, np.where(np.isfinite(ndvi), np.where(in_pilot, 200, 90), 0), OVERLAYS / "ndvi.png")

    stats = {
        "worldcover": {"source_id": "esa_wc", "data_status": "observed", "year": 2021, "item": wc_items[0].id,
                       "classes": {str(k): {"label": v[0], "color": v[1]} for k, v in WC_CLASSES.items()},
                       "pilot_shares_pct": dict(sorted(pilot.items(), key=lambda kv: -kv[1]))},
        "ndvi": {"source_id": "s2_l2a", "data_status": "observed", "window": S2_WINDOW, "scenes": used,
                 "pilot_mean": round(ndvi_pilot, 3), "range_shown": [-0.1, 0.8], "colormap": "RdYlGn",
                 "note": "per-pixel median of low-cloud dry-season scenes; clouds/shadows masked with SCL"},
        "per_catchment": per,
        "overlays": {"worldcover": {"url": f"{OVERLAY_REL}/worldcover.png", "bounds": b4326},
                     "ndvi": {"url": f"{OVERLAY_REL}/ndvi.png", "bounds": b4326}},
        "runoff_c_source": "default",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    OUT_JSON.write_text(json.dumps(stats, indent=1), encoding="utf-8")
    print("WorldCover pilot shares:", stats["worldcover"]["pilot_shares_pct"])
    print(f"NDVI pilot mean {ndvi_pilot:.3f} from {len(used)} scenes {[u['date'] for u in used]} · catchments {len(per)}")
    print("overlays", [f"{p.name} {p.stat().st_size / 1e3:.0f} kB" for p in OVERLAYS.glob("*.png")], "bounds", b4326)


if __name__ == "__main__":
    main()
