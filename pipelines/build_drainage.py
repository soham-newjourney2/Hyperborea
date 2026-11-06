"""P06 step 2: SIMULATED stormwater network for the pilot (D-09) → GPKG layers drains, drain_nodes, outfalls, catchments.

Run after normalize_osm + fetch_dem:  python -m pipelines.build_drainage
Every rule below is an assumption and is written into each feature's `assumptions` text.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
import rasterio
import shapely
from shapely.geometry import LineString, MultiPoint, Point

from backend.engine.hydraulics import MANNING_N, MIN_SLOPE, PIPE_SIZES_M, manning_full_circular
from pipelines.osm_common import ROOT

UTM = 32645
GPKG = ROOT / "data" / "processed" / "hyperborea.gpkg"   # base layers (read)
OUT = ROOT / "data" / "processed" / "drainage.gpkg"     # drainage layers (written; one GPKG per domain, < 5 MB)
DEM = ROOT / "local" / "rasters" / "dem.tif"
NO_INDEX = {"SPATIAL_INDEX": "NO"}

UPHILL_PENALTY_M = 200.0     # extra routing cost per metre climbed (water prefers downhill)
OUTFALL_SNAP_M = 80.0        # a manhole this close to a canal can discharge into it
OUTFALL_SPACING_M = 300.0    # at most one outfall per 300 m (keeps outfalls few, like real systems)
CONDITION_RANGE = (0.6, 1.0)  # siltation / blockage factor, simulated
SEED = 42
RECEIVING = {"canal", "drain", "river", "stream", "ditch"}
FALLBACK_WATER = {"water", "wetland"}  # ponds/wetlands: receiving water only for fragments with no canal (user, P06)
DIAMETER_M = {"trunk": 1.2, "primary": 1.2, "secondary": 1.2, "tertiary": 0.9}  # minimum by road class, else 0.6
# D-20: size each drain for a design storm on everything upstream (rational method), standard pipe sizes.
DESIGN_RAIN_MM_H = 20.0   # assumed design intensity (Salt Lake design standard unknown; KMC legacy ~6 mm/h)
ROAD_HALF_WIDTH_M = {"trunk": 7.0, "primary": 7.0, "secondary": 5.5, "tertiary": 4.0}  # else 3.0
RUNOFF_C = {"roof": 0.90, "road": 0.85, "other": 0.40}

A_DRAIN = ("Simulated side drain along the road (Salt Lake side drains follow roads — assumption); "
           f"diameter = smallest standard pipe carrying the design flow ({DESIGN_RAIN_MM_H:.0f} mm/h on upstream C·A, "
           "rational method), never below the road-class minimum (1.2 / 0.9 / 0.6 m), max 2.4 m; "
           f"Manning full flow n={MANNING_N}; slope = max(DEM slope, {MIN_SLOPE}); condition factor simulated "
           f"U{CONDITION_RANGE} (seed {SEED}); flow direction = shortest path to an outfall with "
           f"{UPHILL_PENALTY_M:.0f} m cost per metre uphill")


def road_class(h) -> str:
    h = str(h or "")
    for k in ("trunk", "primary", "secondary", "tertiary"):
        if h == k or f"'{k}" in h or h.startswith(k):
            return k
    return "other"


def ground_elevation(xs, ys) -> np.ndarray:
    """DEM is a surface model (roofs, trees): use the min of a 3×3 window (~90 m) as a ground proxy."""
    with rasterio.open(DEM) as src:
        arr = src.read(1).astype(float)
        if src.nodata is not None:
            arr[arr == src.nodata] = np.nan
        rows, cols = rasterio.transform.rowcol(src.transform, xs, ys)
    out = []
    for r, c in zip(rows, cols):
        win = arr[max(r - 1, 0): r + 2, max(c - 1, 0): c + 2]
        out.append(float(np.nanmin(win)) if np.isfinite(win).any() else np.nan)
    z = np.array(out)
    return np.where(np.isfinite(z), z, np.nanmedian(z))


def clean_json(o):
    """numpy scalars → Python, NaN/inf → None (browsers reject NaN in JSON)."""
    if isinstance(o, dict):
        return {k: clean_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean_json(v) for v in o]
    if hasattr(o, "item"):
        o = o.item()
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def newest_raw_graph():
    raw = max(p.parent for p in (ROOT / "data" / "raw" / "osm").glob("*/meta.json"))
    return ox.load_graphml(raw / "drive.graphml")


def pick_outfalls(comp: set, nodes: pd.DataFrame, canals: gpd.GeoDataFrame) -> list[dict]:
    sub = nodes.loc[sorted(comp)]
    cand = sub[sub.canal_dist <= OUTFALL_SNAP_M].sort_values("canal_dist")
    chosen: list[dict] = []
    for nid, r in cand.iterrows():
        p = Point(r.x_utm, r.y_utm)
        if all(p.distance(Point(c["x_utm"], c["y_utm"])) >= OUTFALL_SPACING_M for c in chosen):
            chosen.append({"node": nid, "x_utm": r.x_utm, "y_utm": r.y_utm, "snapped": True})
    for c in chosen:
        r = nodes.loc[c["node"]]
        c.update(canal_id=r.canal_id, canal_name=None if pd.isna(r.canal_name) else r.canal_name,
                 canal_dist=float(r.canal_dist), receiving_kind="canal")
    if chosen:
        return chosen
    # No canal nearby: a pond/wetland within the snap distance, else the node nearest a canal (flagged).
    if sub.water_dist.min() <= OUTFALL_SNAP_M:
        nid = sub.water_dist.idxmin()
        r = sub.loc[nid]
        return [{"node": nid, "x_utm": r.x_utm, "y_utm": r.y_utm, "snapped": True, "canal_id": r.water_id,
                 "canal_name": None if pd.isna(r.water_name) else r.water_name, "canal_dist": float(r.water_dist),
                 "receiving_kind": "water body"}]
    nid = sub.canal_dist.idxmin()
    r = sub.loc[nid]
    return [{"node": nid, "x_utm": r.x_utm, "y_utm": r.y_utm, "snapped": False, "canal_id": r.canal_id,
             "canal_name": None if pd.isna(r.canal_name) else r.canal_name, "canal_dist": float(r.canal_dist),
             "receiving_kind": "canal (distant)"}]


def main() -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rng = np.random.default_rng(SEED)
    bnd = gpd.read_file(GPKG, layer="boundary").to_crs(UTM)
    boundary = bnd.geometry.iloc[0]
    roads = gpd.read_file(GPKG, layer="roads")
    roads = roads[roads["in_pilot"].astype(bool)].to_crs(UTM).reset_index(drop=True)
    ra = roads["attrs"].map(json.loads)
    roads = roads.assign(u=ra.map(lambda a: a["u"]), v=ra.map(lambda a: a["v"]), key=ra.map(lambda a: a["key"]),
                         highway=ra.map(lambda a: a.get("highway")), length_m=ra.map(lambda a: a["length_m"]))
    roads["cls"] = roads.highway.map(road_class)

    # Nodes: exact coordinates from the raw OSM drive graph.
    g_osm = newest_raw_graph()
    ids = sorted(set(roads.u) | set(roads.v))
    pts = gpd.GeoSeries([Point(g_osm.nodes[i]["x"], g_osm.nodes[i]["y"]) for i in ids], crs=4326)
    nodes = pd.DataFrame({"lon": pts.x.values, "lat": pts.y.values}, index=ids)
    utm = pts.to_crs(UTM)
    nodes["x_utm"], nodes["y_utm"] = utm.x.values, utm.y.values
    nodes["z"] = ground_elevation(nodes.lon.values, nodes.lat.values)

    # Receiving water: canal-like OSM waterways within 500 m of the pilot.
    ww = gpd.read_file(GPKG, layer="waterways").to_crs(UTM)
    canals = ww[ww.asset_type.isin(RECEIVING) & ww.geom_type.str.contains("Line")]
    canals = canals[canals.distance(boundary) < 500].reset_index(drop=True)
    near = gpd.sjoin_nearest(gpd.GeoDataFrame(geometry=utm.values, crs=UTM, index=ids),
                             canals[["asset_id", "name", "geometry"]], distance_col="canal_dist", how="left")
    near = near[~near.index.duplicated()]
    nodes["canal_dist"], nodes["canal_id"] = near.canal_dist, near.asset_id
    nodes["canal_name"] = [None if pd.isna(x) else x for x in near["name"]]
    water = ww[ww.asset_type.isin(FALLBACK_WATER) & ww.geom_type.str.contains("Polygon")]
    water = water[water.distance(boundary) < 500][["asset_id", "name", "geometry"]].reset_index(drop=True)
    wnear = gpd.sjoin_nearest(gpd.GeoDataFrame(geometry=utm.values, crs=UTM, index=ids), water,
                              distance_col="water_dist", how="left")
    wnear = wnear[~wnear.index.duplicated()]
    nodes["water_dist"], nodes["water_id"], nodes["water_name"] = wnear.water_dist, wnear.asset_id, wnear["name"]

    # Graph + outfalls per connected component.
    G = nx.MultiGraph()
    for i, r in roads.iterrows():
        G.add_edge(r.u, r.v, key=i, length=r.length_m)
    outfalls: list[dict] = []
    for comp in nx.connected_components(G):
        outfalls += pick_outfalls(comp, nodes, canals)
    out_nodes = {o["node"] for o in outfalls}

    # Elevation-aware multi-source Dijkstra on the reversed flow graph → distance-to-outfall + downstream parent.
    R = nx.DiGraph()
    for a, b, d in G.edges(data=True):
        for x, y in ((a, b), (b, a)):  # water x → y costs length + penalty·rise; reversed edge y → x
            w = d["length"] + UPHILL_PENALTY_M * max(0.0, nodes.at[y, "z"] - nodes.at[x, "z"])
            if not R.has_edge(y, x) or R[y][x]["w"] > w:
                R.add_edge(y, x, w=w)
    dist, paths = nx.multi_source_dijkstra(R, out_nodes, weight="w")
    parent = {n: (p[-2] if len(p) > 1 else None) for n, p in paths.items()}
    assert len(dist) == len(nodes), "every node must reach an outfall"

    # Segments: orient upstream → downstream (higher → lower distance), Manning capacity.
    seg_rows, tree_seg = [], {}
    for i, r in roads.iterrows():
        a, b = (r.u, r.v) if (dist[r.u], r.u) > (dist[r.v], r.v) else (r.v, r.u)
        sid = f"drn_syn_{r.u}_{r.v}_{r.key}"
        if parent.get(a) == b and a not in tree_seg:
            tree_seg[a] = sid
        geom = r.geometry
        if Point(geom.coords[0]).distance(Point(nodes.at[a, "x_utm"], nodes.at[a, "y_utm"])) > \
                Point(geom.coords[-1]).distance(Point(nodes.at[a, "x_utm"], nodes.at[a, "y_utm"])):
            geom = LineString(geom.coords[::-1])
        drop = nodes.at[a, "z"] - nodes.at[b, "z"]
        dem_slope = drop / max(r.length_m, 1.0)
        slope = round(max(dem_slope, MIN_SLOPE), 5)  # rounded before use so stored inputs reproduce capacity
        d = DIAMETER_M.get(r.cls, 0.6)
        cond = round(float(rng.uniform(*CONDITION_RANGE)), 2)
        cap = manning_full_circular(d, slope)
        seg_rows.append({"sid": sid, "a": a, "b": b, "road_id": r.asset_id, "cls": r.cls, "highway": r.highway,
                         "length_m": r.length_m, "diameter_m": d, "slope": slope,
                         "slope_source": "dem" if dem_slope >= MIN_SLOPE else f"floor {MIN_SLOPE}",
                         "elev_up_m": round(nodes.at[a, "z"], 2), "elev_down_m": round(nodes.at[b, "z"], 2),
                         "condition_factor": cond, "capacity_m3s": round(cap, 4),
                         "effective_capacity_m3s": round(cap * cond, 4), "geometry": geom})
    segs = gpd.GeoDataFrame(seg_rows, crs=UTM)
    out_id = {o["node"]: f"out_cur_{k:02d}" for k, o in enumerate(sorted(outfalls, key=lambda o: o["node"]), 1)}
    segs["downstream_id"] = [out_id[b] if b in out_nodes else tree_seg[b] for b in segs.b]

    # Upstream counts (topological over the segment forest).
    down = dict(zip(segs.sid, segs.downstream_id))
    T = nx.DiGraph([(s, t) for s, t in down.items()])
    assert nx.is_directed_acyclic_graph(T)
    segs["n_upstream"] = [len(nx.ancestors(T, s)) for s in segs.sid]

    # Catchments: Voronoi of segment midpoints, clipped to the boundary; runoff C area-weighted.
    mids = segs.geometry.interpolate(0.5, normalized=True)
    vor = shapely.voronoi_polygons(MultiPoint(list(mids)), extend_to=boundary.buffer(500))
    cells = gpd.GeoDataFrame(geometry=list(vor.geoms), crs=UTM)
    # Match each (unclipped) cell to its generating midpoint first — midpoints of edge roads can lie just
    # outside the boundary — then clip. Duplicate midpoints share one cell: the first drain keeps it.
    owner = gpd.sjoin(gpd.GeoDataFrame({"sid": segs.sid}, geometry=mids, crs=UTM), cells, predicate="within")
    owner = owner[~owner.index_right.duplicated()]
    cells = cells.loc[owner.index_right].assign(sid=owner.sid.values).reset_index(drop=True)
    cells["geometry"] = cells.intersection(boundary)
    cells = cells[~cells.is_empty & cells.geom_type.isin(["Polygon", "MultiPolygon"])].reset_index(drop=True)
    bld = gpd.read_file(GPKG, layer="buildings").to_crs(UTM)
    roofs = bld.geometry.union_all().intersection(boundary)
    road_poly = shapely.union_all([g.buffer(ROAD_HALF_WIDTH_M.get(c, 3.0)) for g, c in zip(segs.geometry, segs.cls)])
    road_poly = road_poly.difference(roofs).intersection(boundary)
    cells["area_m2"] = cells.area
    cells["roof_m2"] = cells.intersection(roofs).area
    cells["road_m2"] = cells.intersection(road_poly).area
    cells["other_m2"] = (cells.area_m2 - cells.roof_m2 - cells.road_m2).clip(lower=0)
    cells["runoff_c"] = ((RUNOFF_C["roof"] * cells.roof_m2 + RUNOFF_C["road"] * cells.road_m2
                          + RUNOFF_C["other"] * cells.other_m2) / cells.area_m2).round(3)
    cat_of = dict(zip(cells.sid, "cat_syn_" + cells.sid.str.removeprefix("drn_syn_")))
    area_of = dict(zip(cells.sid, cells.area_m2))
    segs["catchment_id"] = segs.sid.map(cat_of)
    segs["catchment_m2"] = segs.sid.map(area_of).fillna(0)
    segs["upstream_area_m2"] = [area_of.get(s, 0) + sum(area_of.get(x, 0) for x in nx.ancestors(T, s))
                                for s in segs.sid]

    # Design-storm sizing (D-20): Q_design = i · ΣC·A / 3.6e6 over the drain and everything upstream.
    ca_of = dict(zip(cells.sid, cells.runoff_c * cells.area_m2))
    segs["upstream_ca_m2"] = [ca_of.get(s, 0) + sum(ca_of.get(x, 0) for x in nx.ancestors(T, s)) for s in segs.sid]
    segs["design_flow_m3s"] = DESIGN_RAIN_MM_H * segs.upstream_ca_m2 / 3.6e6
    sizes, how = [], []
    for q, slope, cls in zip(segs.design_flow_m3s, segs.slope, segs.cls):
        # invert Manning full flow: d = (Q·n·4^(5/3) / (π·√S))^(3/8)
        d_req = (q * MANNING_N * 4 ** (5 / 3) / (math.pi * math.sqrt(slope))) ** 0.375 if q > 0 else 0.0
        need = max(DIAMETER_M.get(cls, 0.6), d_req)
        fit = next((d for d in PIPE_SIZES_M if d >= need - 1e-9), None)
        sizes.append(fit or PIPE_SIZES_M[-1])
        how.append("road-class minimum" if fit and fit == DIAMETER_M.get(cls, 0.6) and d_req <= fit
                   else "design storm" if fit else "max size — undersized for design storm")
    segs["diameter_m"], segs["sizing"] = sizes, how
    segs["capacity_m3s"] = [round(manning_full_circular(d, sl), 4) for d, sl in zip(segs.diameter_m, segs.slope)]
    segs["effective_capacity_m3s"] = (segs.capacity_m3s * segs.condition_factor).round(4)

    # ---- write layers ---------------------------------------------------------------------------
    pilot_area = boundary.buffer(0.5)  # same rule as normalize_osm (UTM, 0.5 m tolerance)
    def frame(rows, geoms, asset_type, status, source, assumptions, conf) -> gpd.GeoDataFrame:
        df = pd.DataFrame(rows)
        return gpd.GeoDataFrame({
            "asset_id": df.pop("asset_id"), "asset_type": asset_type, "name": df.pop("name") if "name" in df else None,
            "data_status": status, "source_id": source, "observed_at": None, "ingested_at": now,
            "confidence": conf, "assumptions": assumptions,
            "attrs": [json.dumps(clean_json(a), allow_nan=False) for a in df.pop("attrs")],
            "in_pilot": [g.representative_point().within(pilot_area) for g in geoms],
        }, geometry=list(geoms), crs=UTM).to_crs(4326)

    drains = frame([{"asset_id": s.sid, "name": None, "attrs": {
        "road_id": s.road_id, "road_class": s.cls, "highway": s.highway, "from_node": f"mh_syn_{s.a}",
        "to_node": f"mh_syn_{s.b}", "drains_to": s.downstream_id, "shape": "circular-equivalent",
        "diameter_m": s.diameter_m, "length_m": s.length_m, "slope": s.slope, "slope_source": s.slope_source,
        "elev_up_m": s.elev_up_m, "elev_down_m": s.elev_down_m, "manning_n": MANNING_N,
        "condition_factor": s.condition_factor, "capacity_m3s": s.capacity_m3s,
        "effective_capacity_m3s": s.effective_capacity_m3s, "n_upstream": int(s.n_upstream),
        "catchment_id": s.catchment_id, "catchment_m2": round(s.catchment_m2, 1),
        "upstream_area_m2": round(s.upstream_area_m2, 1), "upstream_ca_m2": round(s.upstream_ca_m2, 1),
        "design_rain_mm_h": DESIGN_RAIN_MM_H, "design_flow_m3s": round(s.design_flow_m3s, 4), "sizing": s.sizing,
        "formula": "Q = (1/n)·A·R^(2/3)·S^(1/2); A = πd²/4, R = d/4; effective = Q × condition_factor"}}
        for s in segs.itertuples()], segs.geometry, "drain", "simulated", "syn_drain", A_DRAIN, "low")

    down_count = segs.groupby("a").size()
    node_rows = [{"asset_id": f"mh_syn_{n}", "name": None, "attrs": {
        "osm_node": int(n), "ground_elev_m": round(float(r.z), 2), "elev_source": "cop_dem 3×3 min (ground proxy)",
        "dist_to_outfall_m": round(float(dist[n]), 1), "drains_via": tree_seg.get(n) or out_id.get(n),
        "is_outfall": n in out_nodes, "n_out_segments": int(down_count.get(n, 0))}} for n, r in nodes.iterrows()]
    drain_nodes = frame(node_rows, [Point(r.x_utm, r.y_utm) for r in nodes.itertuples()], "manhole", "simulated",
                        "syn_drain", "Simulated junction at each road node; ground level from Copernicus DEM "
                        "(surface model, 3×3 minimum as ground proxy, ~2–4 m vertical error)", "low")

    of_rows = [{"asset_id": out_id[o["node"]], "name": f"Outfall → {o['canal_name'] or 'unnamed ' + o['receiving_kind']}", "attrs": {
        "node": f"mh_syn_{o['node']}", "receiving_water_id": o["canal_id"], "receiving_water": o["canal_name"],
        "receiving_kind": o["receiving_kind"],
        "distance_to_water_m": round(o["canal_dist"], 1), "snapped": o["snapped"],
        "n_upstream_segments": int(sum(1 for s in segs.itertuples() if s.downstream_id == out_id[o["node"]])
                                   + sum(len(nx.ancestors(T, s.sid)) for s in segs.itertuples()
                                         if s.downstream_id == out_id[o["node"]]))}} for o in outfalls]
    outf = frame(of_rows, [Point(o["x_utm"], o["y_utm"]) for o in outfalls], "outfall", "curated", "cur_outfall",
                 f"Placed at manholes ≤ {OUTFALL_SNAP_M:.0f} m from an OSM canal, ≥ {OUTFALL_SPACING_M:.0f} m apart; "
                 f"fragments with no canal use a pond/wetland ≤ {OUTFALL_SNAP_M:.0f} m (user-approved, P06); "
                 "placement confirmed by user 2026-11-06, no municipal records (O-04)", "med")

    cat_rows = [{"asset_id": cat_of[c.sid], "name": None, "attrs": {
        "drain_id": c.sid, "area_m2": round(c.area_m2, 1), "roof_m2": round(c.roof_m2, 1),
        "road_m2": round(c.road_m2, 1), "other_m2": round(c.other_m2, 1), "runoff_c": c.runoff_c,
        "runoff_c_source": "area-weighted: roof 0.90 (OSM buildings), road 0.85 (road buffers), other 0.40"}}
        for c in cells.itertuples()]
    cats = frame(cat_rows, cells.geometry, "catchment", "simulated", "syn_drain",
                 "Voronoi cell of the drain midpoint clipped to the pilot (each cell drains to its nearest drain); "
                 "runoff C area-weighted (planning §7)", "low")

    OUT.unlink(missing_ok=True)
    for name, gdf in (("drains", drains), ("drain_nodes", drain_nodes), ("outfalls", outf), ("catchments", cats)):
        gdf.to_file(OUT, layer=name, driver="GPKG", layer_options=NO_INDEX)

    print(f"drains {len(drains)} · manholes {len(drain_nodes)} · outfalls {len(outf)} "
          f"({sum(o['snapped'] for o in outfalls)} snapped ≤ {OUTFALL_SNAP_M:.0f} m) · catchments {len(cats)} · "
          f"components {nx.number_connected_components(G)}")
    print(f"catchment area {cells.area_m2.sum() / 1e6:.3f} km² vs boundary {boundary.area / 1e6:.3f} km²; "
          f"mean C {np.average(cells.runoff_c, weights=cells.area_m2):.2f}")
    print(f"slope from DEM on {int((segs.slope_source == 'dem').sum())}/{len(segs)} segments; "
          f"effective capacity m³/s: min {segs.effective_capacity_m3s.min():.3f} "
          f"median {segs.effective_capacity_m3s.median():.3f} max {segs.effective_capacity_m3s.max():.3f}")
    print("sizing:", segs.sizing.value_counts().to_dict(), "· diameters:", segs.diameter_m.value_counts().sort_index().to_dict())
    for o in sorted(outfalls, key=lambda o: out_id[o["node"]]):
        print(f"  {out_id[o['node']]}: {o['canal_name'] or 'unnamed'} [{o['receiving_kind']}] {o['canal_dist']:.0f} m "
              f"{'snapped' if o['snapped'] else 'UNSNAPPED'}")


if __name__ == "__main__":
    main()
