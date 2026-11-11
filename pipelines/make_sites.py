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

from backend.app.core import regions as R  # noqa: E402  (P16: HYPERBOREA_REGION → paths, CRS, timezone)

UTM = R.metric_crs()
SIZE_M, STEP_M = 40.0, 25.0
OK_LANDUSE = ["commercial", "industrial", "construction", "retail", "grass"]
G, D = R.data_dir("processed") / "hyperborea.gpkg", R.data_dir("processed") / "drainage.gpkg"
OUT = R.data_dir("curated") / "sites.geojson"


def search(bnd, lu, blocked, cats, depth, size, need_landuse: bool) -> list[dict]:
    x0, y0, x1, y1 = bnd.bounds
    cells = []
    for x in np.arange(x0, x1, STEP_M):
        for y in np.arange(y0, y1, STEP_M):
            b = box(x, y, x + size, y + size)
            if not b.within(bnd) or b.intersects(blocked):
                continue
            hit = lu[lu.contains(b)]
            if hit.empty and need_landuse:
                continue
            c = cats[cats.intersects(b.centroid)]
            cid = c.asset_id.iloc[0] if len(c) else None
            cells.append({"geom": b, "landuse": hit.asset_type.iloc[0] if len(hit) else "unmapped",
                          "landuse_id": hit.asset_id.iloc[0] if len(hit) else None,
                          "catchment_id": cid, "extreme_depth_m": depth.get(cid, 0.0)})
    return cells


def extreme_depths() -> dict[str, float]:
    """Catchment ponding under the `extreme` preset: Sector V from its frozen snapshot (P09), others from the engine."""
    if R.current() == R.DEFAULT:
        extreme = json.loads((R.data_dir("snapshots") / "flood_extreme.json").read_text(encoding="utf-8"))
        return {k: v["depth_m"] for k, v in extreme["layers"]["catchments"].items()}
    from backend.app.api.scenarios import FloodRequest, flood_context, resolve
    from backend.engine.flood import run_flood
    res = run_flood(flood_context(), resolve(FloodRequest(preset="extreme")))
    return {k: v["depth_m"] for k, v in res["layers"]["catchments"].items()}


def _side(p, bnd) -> str:
    c = bnd.centroid
    dx, dy = p.x - c.x, p.y - c.y
    if abs(dx) < 250 and abs(dy) < 250:
        return "centre"
    ns = "north" if dy > 250 else "south" if dy < -250 else ""
    ew = "east" if dx > 250 else "west" if dx < -250 else ""
    return "-".join(x for x in (ns, ew) if x)


def sector_v_pools(cells):
    return [
        ("S1", "Construction plot (centre-west)", [c for c in cells if c["landuse"] == "construction"]),
        ("S2", "Industrial plot (north-east, flood-prone)", sorted([c for c in cells if c["extreme_depth_m"] > 0],
                                                                  key=lambda c: -c["extreme_depth_m"])),
        ("S3", "Commercial plot (centre)", [c for c in cells if c["extreme_depth_m"] == 0 and c["landuse"] != "construction"]),
    ]


def generic_pools(cells, bnd):
    """S1 a dry plot (prefers construction/commercial), S2 the wettest plot, S3 a dry plot nearest the centre."""
    dry = [c for c in cells if c["extreme_depth_m"] == 0]
    rank = {"construction": 0, "commercial": 1, "industrial": 2, "retail": 3, "grass": 4}
    s1 = sorted(dry, key=lambda c: (rank.get(c["landuse"], 9), -c["geom"].centroid.distance(bnd.centroid)))
    s2 = sorted([c for c in cells if c["extreme_depth_m"] > 0], key=lambda c: -c["extreme_depth_m"])
    s3 = sorted(dry, key=lambda c: c["geom"].centroid.distance(bnd.centroid))
    t = lambda c, what: f"{what} ({c['landuse']}, {_side(c['geom'].centroid, bnd)})"  # noqa: E731
    return [("S1", lambda c: t(c, "Dry plot"), s1), ("S2", lambda c: t(c, "Flood-prone plot"), s2),
            ("S3", lambda c: t(c, "Central plot"), s3)]


def main() -> None:
    bnd = gpd.read_file(G, layer="boundary").to_crs(UTM).geometry.iloc[0]
    lu = gpd.read_file(G, layer="landuse")
    lu = lu[lu.in_pilot.astype(bool) & lu.asset_type.isin(OK_LANDUSE)].to_crs(UTM)
    blocked = shapely.union_all(
        list(gpd.read_file(G, layer="buildings").to_crs(UTM).buffer(3).geometry)
        + list(gpd.read_file(G, layer="roads").to_crs(UTM).buffer(5).geometry)
        + list(gpd.read_file(G, layer="waterways").to_crs(UTM).buffer(5).geometry))
    cats = gpd.read_file(D, layer="catchments").to_crs(UTM)
    depth = extreme_depths()

    cells = search(bnd, lu, blocked, cats, depth, SIZE_M, need_landuse=True)
    if R.current() != R.DEFAULT and len(cells) < 3:  # P17: sparse OSM land use (e.g. Velachery) → unmapped open land
        cells = search(bnd, lu, blocked, cats, depth, SIZE_M, need_landuse=False) or             search(bnd, lu, blocked, cats, depth, 30.0, need_landuse=False)
    picks: list[dict] = []
    far = lambda c: all(c["geom"].centroid.distance(p["geom"].centroid) > 400 for p in picks)  # noqa: E731
    pools = sector_v_pools(cells) if R.current() == R.DEFAULT else generic_pools(cells, bnd)
    for sid, title, pool in pools:
        c = next((c for c in pool if far(c)), None)
        if c:
            picks.append({**c, "site_id": sid, "title": title(c) if callable(title) else title})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    gdf = gpd.GeoDataFrame({
        "asset_id": [f"site_cur_{p['site_id'].lower()}" for p in picks],
        "asset_type": "candidate_site",
        "name": [f"{p['site_id']} · {p['title']}" for p in picks],
        "data_status": "curated", "source_id": "cur_sites", "observed_at": None, "ingested_at": now,
        "confidence": "med",
        "assumptions": [("Candidate site assumed vacant: building-free "
                         f"{round(p['geom'].area ** 0.5)} × {round(p['geom'].area ** 0.5)} m plot "
                         + ("inside OSM land use; " if p["landuse"] != "unmapped" else "with no OSM land use mapped (open land in OSM); ")
                         + "not a planning allocation, ownership unknown") for p in picks],
        "attrs": [json.dumps({"site_id": p["site_id"], "landuse": p["landuse"], "landuse_id": p["landuse_id"],
                              "catchment_id": p["catchment_id"], "area_m2": round(p["geom"].area, 1),
                              "extreme_preset_ponding_m": p["extreme_depth_m"]}) for p in picks],
        "in_pilot": True,
    }, geometry=[p["geom"] for p in picks], crs=UTM).to_crs(4326)
    if gdf.empty:
        raise SystemExit("no candidate site found — check OSM land use / building coverage")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(OUT, driver="GeoJSON")
    print(f"{len(cells)} free cells → {len(gdf)} sites:", ", ".join(gdf.name))


if __name__ == "__main__":
    main()
