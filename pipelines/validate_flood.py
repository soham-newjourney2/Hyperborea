"""P22: score the flood engine against an observed flood extent — Chennai Velachery, December 2015.

Observed: Sentinel-1 RTC (Planetary Computer, CC BY 4.0) VV backscatter, descending orbit 92.
  reference = median of dry-season passes (2015-03-05, 2015-05-28, 2016-02-28); post-event = 2015-12-06.
  water = 3×3 median-filtered dB < -15; flood = water now & not water in the reference & drop > 3 dB.
  SAR misses water between buildings (double bounce / shadow) → catchment fractions use open (non-building) pixels only.
Modelled: engine runs with three rain inputs (ERA5 as-is; 286 mm/24 h station average from World Weather Attribution;
  286 mm with ERA5's hourly timing). Compared per catchment: observed flooded if ≥ OBS_FRAC of its open pixels are
  flood; predicted flooded if ponding ≥ PRED_DEPTH_M. Naive baseline: the same number of lowest-lying catchments.
Run:  $env:HYPERBOREA_REGION='chennai_velachery'; python -m pipelines.validate_flood
Out:  data/regions/<id>/processed/{validation.json, sar_flood.gpkg}
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import geopandas as gpd
import httpx
import numpy as np
import planetary_computer
import pystac_client
import rasterio
import rasterio.features
import rioxarray  # noqa: F401
import xarray as xr
from scipy.ndimage import median_filter
from shapely.geometry import shape

from backend.app.core import regions as R
from backend.engine.validation import auc, scores, worst

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
EVENT = {
    "chennai_velachery": {
        "name": "Chennai floods, 1–2 December 2015",
        "reference_dates": ["2015-03-05", "2015-05-28", "2016-02-28"],
        "post_date": "2015-12-06",
        "control_date": "2015-12-18",  # after the water receded: brightening should mostly vanish
        "rain_window": ("2015-11-30", "2015-12-02"),
        "station_total_mm": 286.0, "station_hours": 24, "station_start": "2015-12-01T08:00",
        "station_source": "World Weather Attribution (2015): mean of station 24-h totals 08:30 1 Dec – 08:30 2 Dec 2015",
        "context": "Post-event pass 4–5 days after the peak; Velachery stayed waterlogged for days. Lake/river releases "
                   "(Chembarambakkam → Adyar) and backwater from Pallikaranai marsh are NOT in the engine.",
    },
}
WATER_DB, DROP_DB, OBS_FRAC, PRED_DEPTH_M, MIN_POLY_M2 = -15.0, 3.0, 0.10, 0.15, 300.0
RISE_DB, URBAN_FRAC = 3.0, 0.30  # urban flood indicator: VV brighter by > 3 dB next to buildings (double bounce)
OUT = R.data_dir("processed")


def vv_db(cat, date: str, bbox4326) -> xr.DataArray:
    items = list(cat.search(collections=["sentinel-1-rtc"], bbox=bbox4326, datetime=date).items())
    if not items:
        raise SystemExit(f"no Sentinel-1 RTC item on {date}")
    da = xr.open_dataarray(items[0].assets["vv"].href, engine="rasterio").squeeze(drop=True)
    utm = R.metric_crs()
    b = gpd.GeoSeries.from_xy([bbox4326[0], bbox4326[2]], [bbox4326[1], bbox4326[3]], crs=4326).to_crs(da.rio.crs).total_bounds
    da = da.rio.clip_box(*b).astype("float32")
    da = da.where(da > 0)
    db = 10 * np.log10(da)
    return db.rio.reproject(utm) if da.rio.crs.to_epsg() != utm else db


def era5_hourly(lat: float, lon: float, start: str, end: str) -> tuple[list[str], list[float]]:
    r = httpx.get("https://archive-api.open-meteo.com/v1/archive", timeout=60, params={
        "latitude": lat, "longitude": lon, "start_date": start, "end_date": end, "hourly": "precipitation",
        "models": "era5", "timezone": R.cfg()["timezone"]})
    r.raise_for_status()
    h = r.json()["hourly"]
    return h["time"], [float(x or 0) for x in h["precipitation"]]


def main() -> None:
    rid = R.current()
    ev = EVENT.get(rid)
    if ev is None:
        raise SystemExit(f"no validation event configured for {rid}")
    from backend.app.api.scenarios import flood_context
    from backend.engine.flood import run_flood

    utm = R.metric_crs()
    G = R.data_dir("processed") / "hyperborea.gpkg"
    bnd = gpd.read_file(G, layer="boundary")
    bbox = list(bnd.to_crs(utm).buffer(300).to_crs(4326).total_bounds)
    cat = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)

    # ---- observed flood from Sentinel-1 ----
    refs = [vv_db(cat, d, bbox) for d in ev["reference_dates"]]
    post = vv_db(cat, ev["post_date"], bbox)
    refs = [r.rio.reproject_match(post) for r in refs]
    ref = xr.concat(refs, "t").median("t")
    f = lambda a: median_filter(np.nan_to_num(a.values, nan=0.0), size=3)  # noqa: E731
    post_f, ref_f = f(post), f(ref)
    perm = ref_f < WATER_DB
    flood = (post_f < WATER_DB) & ~perm & ((post_f - ref_f) < -DROP_DB)
    ctl_f = f(vv_db(cat, ev["control_date"], bbox).rio.reproject_match(post))
    tr = post.rio.transform()
    px = abs(tr.a * tr.e)
    cats = gpd.read_file(R.data_dir("processed") / "drainage.gpkg", layer="catchments").to_crs(utm)
    blds = gpd.read_file(G, layer="buildings").to_crs(utm)
    bmask = rasterio.features.geometry_mask(blds.geometry, post_f.shape, tr, invert=True)
    near_b = rasterio.features.geometry_mask(blds.buffer(10).geometry, post_f.shape, tr, invert=True)  # building + 10 m
    urban = ((post_f - ref_f) > RISE_DB) & near_b & ~perm
    urban_ctl = ((ctl_f - ref_f) > RISE_DB) & near_b & ~perm
    obs_frac, urb_frac = {}, {}
    for cid, geom in zip(cats.asset_id, cats.geometry):
        cm = rasterio.features.geometry_mask([geom], post_f.shape, tr, invert=True)
        m = cm & ~bmask & ~perm
        n = int(m.sum())
        obs_frac[cid] = (float(flood[m].mean()) if n >= 5 else None, n)
        u = cm & near_b & ~perm
        urb_frac[cid] = float(urban[u].mean()) if u.sum() >= 5 else None
    valid = {c for c in cats.asset_id if obs_frac[c][0] is not None or urb_frac[c] is not None}
    obs_open = {c for c in valid if (obs_frac[c][0] or 0) >= OBS_FRAC}
    obs_urban = {c for c in valid if (urb_frac[c] or 0) >= URBAN_FRAC}
    obs = obs_open | obs_urban
    near_n = int(near_b.sum()) or 1
    urban_share, control_share = float(urban.sum()) / near_n, float(urban_ctl.sum()) / near_n

    # polygons for the map
    cls = np.where(flood, 1, np.where(urban, 2, 0)).astype("uint8")
    polys = [(shape(g), int(v)) for g, v in rasterio.features.shapes(cls, mask=cls > 0, transform=tr)]
    polys = [(p, v) for p, v in polys if p.area >= MIN_POLY_M2]
    kinds = {1: "open water (radar darkening)", 2: "urban flood indicator (radar brightening, lower confidence)"}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lay = gpd.GeoDataFrame({
        "asset_id": [f"sar_obs_{i:04d}" for i in range(len(polys))], "asset_type": "observed_flood",
        "name": [f"SAR {kinds[v].split(' (')[0]} {round(p.area)} m²" for p, v in polys], "data_status": "modelled", "source_id": "s1_rtc",
        "observed_at": ev["post_date"], "ingested_at": now, "confidence": ["med" if v == 1 else "low" for _, v in polys],
        "assumptions": ["Sentinel-1 VV < -15 dB and > 3 dB below the dry-season median on open ground (not water before)"
                        if v == 1 else "Sentinel-1 VV > 3 dB above the dry-season median within 10 m of buildings — "
                        "double bounce from water between walls; wet surfaces also brighten (lower confidence)"
                        for _, v in polys],
        "attrs": [json.dumps({"area_m2": round(p.area, 1), "event": ev["name"], "class": kinds[v]}) for p, v in polys],
        "in_pilot": True,
    }, geometry=[p.simplify(5) for p, _ in polys], crs=utm).to_crs(4326)
    lay = lay[lay.intersects(bnd.geometry.iloc[0])]
    lay.to_file(OUT / "sar_flood.gpkg", layer="sar_flood", driver="GPKG", SPATIAL_INDEX="NO")

    # ---- modelled runs ----
    c = bnd.to_crs(utm).centroid.to_crs(4326).iloc[0]
    times, p = era5_hourly(c.y, c.x, *ev["rain_window"])
    s0 = times.index(ev["station_start"]) if ev["station_start"] in times else 0
    era_24 = sum(p[s0:s0 + ev["station_hours"]]) or 1e-9
    scaled = [x * ev["station_total_mm"] / era_24 for x in p]
    i6, w6 = worst(p, 6)
    j6, v6 = worst(scaled, 6)
    runs = {
        "A_era5": {"label": "ERA5 hourly as-is, worst 6 h", "rain_mm_h": round(w6 / 6, 2), "duration_h": 6.0,
                   "source_id": "om_archive", "window_start": times[i6]},
        "B_station_uniform": {"label": f"{ev['station_total_mm']:.0f} mm in 24 h, uniform", "duration_h": 24.0,
                              "rain_mm_h": round(ev["station_total_mm"] / 24, 2), "source_id": "wwa_chennai_2015"},
        "C_station_era5_timing": {"label": f"{ev['station_total_mm']:.0f} mm with ERA5 timing, worst 6 h",
                                  "rain_mm_h": round(v6 / 6, 2), "duration_h": 6.0, "source_id": "wwa_chennai_2015",
                                  "window_start": times[j6]},
    }
    ctx = flood_context()
    universe = valid
    dem_low = {}
    try:
        with rasterio.open(R.local_dir("rasters") / "dem.tif") as src:
            for cid, geom in zip(cats.asset_id, cats.to_crs(src.crs).geometry):
                pt = geom.representative_point()
                dem_low[cid] = float(next(src.sample([(pt.x, pt.y)]))[0])
    except Exception:  # noqa: BLE001
        pass
    results = {}
    for k, r in runs.items():
        res = run_flood(ctx, {"preset": None, "preset_source_id": r["source_id"], "rain_mm_h": r["rain_mm_h"],
                              "duration_h": r["duration_h"], "condition_scale": 1.0})
        depth = {cid: float(v.get("depth_m") or 0) for cid, v in res["layers"]["catchments"].items()}
        pred = {cid for cid, d in depth.items() if d >= PRED_DEPTH_M} & universe
        low = set(sorted((c for c in universe if c in dem_low), key=lambda c: dem_low[c])[:len(pred)]) if pred else set()
        results[k] = {**r, "predicted_flooded": len(pred), "engine": scores(obs, pred, universe),
                      "engine_vs_open_water": scores(obs_open, pred, universe),
                      "engine_vs_urban_indicator": scores(obs_urban, pred, universe),
                      "baseline_lowest_ground": scores(obs, low, universe),
                      "drains_overloaded": res["summary"]["drains_overloaded"], "drains_total": res["summary"]["drains_total"],
                      "auc_engine_depth": auc(obs, {c: depth.get(c, 0.0) for c in universe}),
                      "auc_lowest_ground": auc(obs, {c: -dem_low[c] for c in universe if c in dem_low})}
        print(k, r["rain_mm_h"], "mm/h ×", r["duration_h"], "h →", len(pred), "catchments;", results[k]["engine"],
              "| baseline", results[k]["baseline_lowest_ground"], "| AUC engine", results[k]["auc_engine_depth"],
              "lowest ground", results[k]["auc_lowest_ground"])

    out = {
        "region": rid, "event": ev["name"], "context": ev["context"], "generated_at": now,
        "observed": {"source_id": "s1_rtc", "data_status": "modelled",
                     "label": "Flood extent from Sentinel-1 radar (observation-derived, thresholded)",
                     "post_date": ev["post_date"], "reference_dates": ev["reference_dates"],
                     "flood_area_m2": round(float(flood.sum()) * px, 0), "polygons": int(len(lay)),
                     "catchments_compared": len(universe), "catchments_flooded": len(obs),
                     "catchments_open_water": len(obs_open), "catchments_urban_indicator": len(obs_urban),
                     "urban_brightening_share_post": round(urban_share, 3),
                     "urban_brightening_share_control": round(control_share, 3), "control_date": ev["control_date"],
                     "rule": f"open water: < {WATER_DB} dB and > {DROP_DB} dB darker than the dry median on open ground "
                             f"(catchment ≥ {int(OBS_FRAC * 100)} % of open pixels); urban indicator: > {RISE_DB} dB brighter "
                             f"within 10 m of buildings (catchment ≥ {int(URBAN_FRAC * 100)} % of those pixels)"},
        "rain": {"era5_event_total_mm": round(sum(p), 1), "era5_peak_mm_h": max(p),
                 "station_total_mm": ev["station_total_mm"], "station_source": ev["station_source"]},
        "predicted_rule": f"catchment ponding ≥ {PRED_DEPTH_M} m",
        "runs": results,
        "metrics_help": {"pod": "hit rate: share of observed-flooded catchments the model flagged",
                         "far": "false-alarm ratio: share of flagged catchments not observed flooded",
                         "csi": "critical success index: hits / (hits + misses + false alarms)"},
        "limitations": [
            "Sentinel-1 cannot see water between buildings; dense blocks are under-counted as observed.",
            "Single post-event pass, 4–5 days after peak rain: some water had drained, some came from lake/river releases.",
            "The engine has no rivers, lakes, tides or pumps and uses simulated drains — this scores the screening "
            "engine, not a calibrated hydraulic model.",
            "ERA5 (~25 km) strongly underestimates the local rain; run C rescales it to the reported station average.",
        ],
    }
    (OUT / "validation.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"urban brightening share post {urban_share:.3f} vs control {control_share:.3f}; open {len(obs_open)}, urban {len(obs_urban)}")
    print(f"observed: {len(obs)}/{len(universe)} catchments flooded, {out['observed']['flood_area_m2']:.0f} m², "
          f"{len(lay)} polygons → {OUT}")


if __name__ == "__main__":
    main()
