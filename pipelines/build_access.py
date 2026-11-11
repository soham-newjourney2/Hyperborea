"""P12: compact drive graph for travel-time accessibility → data/processed/drive_graph.json.

Free-flow travel times (OSM maxspeed where tagged, else assumed urban class speeds) — NOT live traffic.
Buildings and facilities are pre-snapped to their nearest graph node so the API only needs networkx.
Run after normalize_osm:  python -m pipelines.build_access
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import geopandas as gpd
import osmnx as ox

from backend.app.core import regions as R  # noqa: E402  (P16: HYPERBOREA_REGION → paths, CRS, timezone)

OUT = R.data_dir("processed") / "drive_graph.json"
# Assumed free-flow urban speeds (km/h) for Salt Lake when OSM has no maxspeed.
HWY_SPEEDS = {"motorway": 60, "trunk": 50, "primary": 40, "secondary": 30, "tertiary": 25, "unclassified": 20,
              "residential": 20, "living_street": 10, "service": 15, "motorway_link": 40, "trunk_link": 35,
              "primary_link": 30, "secondary_link": 25, "tertiary_link": 20}


def main() -> None:
    raw = max(p.parent for p in (R.data_dir("raw") / "osm").glob("*/meta.json"))
    G = ox.load_graphml(raw / "drive.graphml")
    G = ox.routing.add_edge_speeds(G, hwy_speeds=HWY_SPEEDS, fallback=20)
    G = ox.routing.add_edge_travel_times(G)

    roads = gpd.read_file(R.data_dir("processed") / "hyperborea.gpkg", layer="roads")
    ra = roads["attrs"].map(json.loads)
    road_of = {}
    for aid, a in zip(roads.asset_id, ra):
        road_of[(a["u"], a["v"], a["key"])] = aid
        road_of.setdefault((a["v"], a["u"], a["key"]), aid)
    by_pair = {(u, v): aid for (u, v, _), aid in road_of.items()}

    edges = []
    for u, v, k, d in G.edges(keys=True, data=True):
        rid = road_of.get((u, v, k)) or by_pair.get((u, v)) or by_pair.get((v, u))
        hw = d.get("highway")
        edges.append([int(u), int(v), round(float(d["length"]), 1), round(float(d["travel_time"]), 1),
                      hw if isinstance(hw, str) else str(hw), rid])
    nodes = [[int(n), round(d["x"], 6), round(d["y"], 6)] for n, d in G.nodes(data=True)]

    def snap(gdf):
        pts = gdf.to_crs(R.metric_crs()).representative_point().to_crs(4326)
        ids = ox.distance.nearest_nodes(G, pts.x.values, pts.y.values)
        return dict(zip(gdf.asset_id, (int(i) for i in ids)))

    blds = gpd.read_file(R.data_dir("processed") / "hyperborea.gpkg", layer="buildings")
    fac = gpd.read_file(R.data_dir("processed") / "hyperborea.gpkg", layer="facilities")
    fac_nodes = snap(fac)
    out = {
        "source_id": "osm", "data_status": "modelled",
        "note": "free-flow travel times from OSM maxspeed or assumed class speeds — not live traffic",
        "hwy_speeds_kmh": HWY_SPEEDS, "raw": raw.name,
        "nodes": nodes, "edges": edges,
        "building_nodes": snap(blds),
        "facilities": {fid: {"node": fac_nodes[fid], "type": t, "name": nm if isinstance(nm, str) else None,
                             "in_pilot": bool(ip)}
                       for fid, t, nm, ip in zip(fac.asset_id, fac.asset_type, fac["name"], fac.in_pilot)},
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    unmapped = sum(e[5] is None for e in edges)
    print(f"nodes {len(nodes)} · edges {len(edges)} ({unmapped} without a road asset) · buildings {len(out['building_nodes'])} "
          f"· facilities {len(out['facilities'])} · {OUT.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
