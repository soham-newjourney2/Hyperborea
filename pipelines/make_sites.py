"""P09: candidate development sites (curated, user-confirmed 2026-11-06) → data/curated/sites.geojson.

Search: 40 × 40 m squares on a 25 m grid inside the pilot, fully inside OSM landuse commercial / industrial /
construction / retail / grass, clear of buildings (3 m), roads (5 m) and water (5 m). Picks, ≥ 400 m apart:
S1 on the construction site, S2 the wettest plot in the extreme preset, S3 a dry commercial/industrial plot.
Run after build_drainage + make_snapshots (needs flood_extreme.json):  python -m pipelines.make_sites
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import geopandas as gpd
import numpy as np
import shapely
from shapely.geometry import box

from pipelines.osm_common import ROOT

UTM = 32645
SIZE_M, STEP_M = 40.0, 25.0
OK_LANDUSE = ["commercial", "industrial", "construction", "retail", "grass"]
G, D = ROOT / "data" / "processed" / "hyperborea.gpkg", ROOT / "data" / "processed" / "drainage.gpkg"
OUT = ROOT / "data" / "curated" / "sites.geojson"


def main() -> None:
    bnd = gpd.read_file(G, layer="boundary").to_crs(UTM).geometry.iloc[0]
    lu = gpd.read_file(G, layer="landuse")
    lu = lu[lu.in_pilot.astype(bool) & lu.asset_type.isin(OK_LANDUSE)].to_crs(UTM)
    blocked = shapely.union_all(
        list(gpd.read_file(G, layer="buildings").to_crs(UTM).buffer(3).geometry)
        + list(gpd.read_file(G, layer="roads").to_crs(UTM).buffer(5).geometry)
        + list(gpd.read_file(G, layer="waterways").to_crs(UTM).buffer(5).geometry))
    cats = gpd.read_file(D, layer="catchments").to_crs(UTM)
    extreme = json.loads((ROOT / "data" / "snapshots" / "flood_extreme.json").read_text(encoding="utf-8"))
    depth = {k: v["depth_m"] for k, v in extreme["layers"]["catchments"].items()}

    x0, y0, x1, y1 = bnd.bounds
    cells = []
    for x in np.arange(x0, x1, STEP_M):
        for y in np.arange(y0, y1, STEP_M):
            b = box(x, y, x + SIZE_M, y + SIZE_M)
            if not b.within(bnd) or b.intersects(blocked):
                continue
            hit = lu[lu.contains(b)]
            if hit.empty:
                continue
            c = cats[cats.intersects(b.centroid)]
            cid = c.asset_id.iloc[0] if len(c) else None
            cells.append({"geom": b, "landuse": hit.asset_type.iloc[0], "landuse_id": hit.asset_id.iloc[0],
                          "catchment_id": cid, "extreme_depth_m": depth.get(cid, 0.0)})
    picks: list[dict] = []
    far = lambda c: all(c["geom"].centroid.distance(p["geom"].centroid) > 400 for p in picks)  # noqa: E731
    pools = [
        ("S1", "Construction plot (centre-west)", [c for c in cells if c["landuse"] == "construction"]),
        ("S2", "Industrial plot (north-east, flood-prone)", sorted([c for c in cells if c["extreme_depth_m"] > 0],
                                                                  key=lambda c: -c["extreme_depth_m"])),
        ("S3", "Commercial plot (centre)", [c for c in cells if c["extreme_depth_m"] == 0 and c["landuse"] != "construction"]),
    ]
    for sid, title, pool in pools:
        c = next((c for c in pool if far(c)), None)
        if c:
            picks.append({**c, "site_id": sid, "title": title})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    gdf = gpd.GeoDataFrame({
        "asset_id": [f"site_cur_{p['site_id'].lower()}" for p in picks],
        "asset_type": "candidate_site",
        "name": [f"{p['site_id']} · {p['title']}" for p in picks],
        "data_status": "curated", "source_id": "cur_sites", "observed_at": None, "ingested_at": now,
        "confidence": "med",
        "assumptions": "Candidate site assumed vacant: building-free 40 × 40 m plot inside OSM land use; "
                       "not a planning allocation, ownership unknown",
        "attrs": [json.dumps({"site_id": p["site_id"], "landuse": p["landuse"], "landuse_id": p["landuse_id"],
                              "catchment_id": p["catchment_id"], "area_m2": round(p["geom"].area, 1),
                              "extreme_preset_ponding_m": p["extreme_depth_m"]}) for p in picks],
        "in_pilot": True,
    }, geometry=[p["geom"] for p in picks], crs=UTM).to_crs(4326)
    gdf.to_file(OUT, driver="GeoJSON")
    print(f"{len(cells)} free cells → {len(gdf)} sites:", ", ".join(gdf.name))


if __name__ == "__main__":
    main()
