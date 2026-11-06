"""P07 relationship engine: one typed, explainable dependency graph across asset types.

`build_graph(layers)` takes {layer_id: GeoDataFrame} (EPSG:4326, shared schema §6) so it is testable without the
GeoPackage. Every edge carries relationship_id, type, rule, weight, unit, data_status, confidence, assumptions.
"""
from __future__ import annotations

import json
from collections import Counter, deque

import geopandas as gpd
import networkx as nx

from .relationships import EDGE_TYPES, LAYER_KIND

UTM = 32645
ACCESS_MAX_M = 50.0
DEPENDS_K = 3


def _attrs(gdf: gpd.GeoDataFrame):
    return gdf["attrs"].map(lambda s: json.loads(s) if isinstance(s, str) else (s or {}))


def add_edge(G: nx.MultiDiGraph, etype: str, src: str, tgt: str, *, rule: str, weight: float | None = None,
             unit: str = "", data_status: str, confidence: str, assumptions: str = "") -> None:
    if etype not in EDGE_TYPES:
        raise KeyError(f"edge type {etype} not in registry")
    if src not in G or tgt not in G or not rule:
        return
    G.add_edge(src, tgt, key=etype, relationship_id=f"{etype}:{src}->{tgt}", type=etype, rule=rule,
               weight=None if weight is None else round(float(weight), 3), unit=unit, data_status=data_status,
               confidence=confidence, assumptions=assumptions)


def _access_conf(d: float) -> str:
    return "high" if d <= 15 else "med" if d <= 35 else "low"


def build_graph(layers: dict[str, gpd.GeoDataFrame]) -> nx.MultiDiGraph:
    G = nx.MultiDiGraph()
    for name, kind in LAYER_KIND.items():
        g = layers.get(name)
        if g is None or g.empty:
            continue
        pts = g.to_crs(UTM).representative_point().to_crs(4326)
        for aid, atype, nm, ds, src, p in zip(g.asset_id, g.asset_type, g["name"], g.data_status, g.source_id, pts):
            G.add_node(aid, kind=kind, layer=name, asset_type=atype, name=nm if isinstance(nm, str) else None,
                       data_status=ds, source_id=src, lon=round(p.x, 6), lat=round(p.y, 6))

    drains, roads = layers.get("drains"), layers.get("roads")
    if drains is not None and not drains.empty:
        for aid, a in zip(drains.asset_id, _attrs(drains)):
            add_edge(G, "DRAINS_TO", aid, a.get("drains_to"), weight=a.get("effective_capacity_m3s"), unit="m³/s",
                     rule="P06 routing: flows to the next drain/outfall on the elevation-penalised shortest path "
                          "to an outfall", data_status="simulated", confidence="low",
                     assumptions="simulated network topology (D-09)")
            add_edge(G, "ADJACENT_TO", aid, a.get("road_id"), weight=a.get("length_m"), unit="m",
                     rule="drain generated along this road edge (one side drain per road edge)",
                     data_status="simulated", confidence="low", assumptions="side drains follow roads (P06)")
            add_edge(G, "LOCATED_WITHIN", aid, a.get("catchment_id"), weight=a.get("catchment_m2"), unit="m²",
                     rule="this drain's midpoint generates the Voronoi catchment it collects from",
                     data_status="simulated", confidence="low")

    # Nearest-road access for buildings + facilities (UTM metres).
    if roads is not None and not roads.empty:
        r = roads[["asset_id", "geometry"]].to_crs(UTM).rename(columns={"asset_id": "road_id"})
        for name in ("buildings", "facilities"):
            g = layers.get(name)
            if g is None or g.empty:
                continue
            pts = gpd.GeoDataFrame({"asset_id": g.asset_id.values}, geometry=g.to_crs(UTM).representative_point().values,
                                   crs=UTM)
            near = gpd.sjoin_nearest(pts, r, max_distance=ACCESS_MAX_M, distance_col="d", how="inner")
            near = near.sort_values("d").drop_duplicates("asset_id")
            for aid, rid, d in zip(near.asset_id, near.road_id, near.d):
                add_edge(G, "ACCESSIBLE_VIA", aid, rid, weight=d, unit="m",
                         rule=f"nearest road edge within {ACCESS_MAX_M:.0f} m (distance {d:.0f} m)",
                         data_status="modelled", confidence=_access_conf(d),
                         assumptions="entrance assumed on the nearest road edge")
            if name == "facilities":
                cand = gpd.sjoin(pts.set_geometry(pts.buffer(ACCESS_MAX_M)), r, predicate="intersects")
                cand["d"] = [pts.geometry.iloc[i].distance(r.geometry.loc[j])
                             for i, j in zip(cand.index, cand.index_right)]
                for aid, grp in cand.sort_values("d").groupby("asset_id"):
                    for rid, d in zip(grp.road_id.head(DEPENDS_K), grp.d.head(DEPENDS_K)):
                        add_edge(G, "DEPENDS_ON", aid, rid, weight=d, unit="m",
                                 rule=f"access road within {ACCESS_MAX_M:.0f} m ({d:.0f} m; up to {DEPENDS_K} nearest)",
                                 data_status="modelled", confidence=_access_conf(d),
                                 assumptions="facility unusable if all its access roads are impassable")

    # Containment in catchments (buildings, manholes).
    cats = layers.get("catchments")
    if cats is not None and not cats.empty:
        c = cats[["asset_id", "geometry"]].to_crs(UTM).rename(columns={"asset_id": "catchment_id"})
        for name in ("buildings", "drain_nodes"):
            g = layers.get(name)
            if g is None or g.empty:
                continue
            pts = gpd.GeoDataFrame({"asset_id": g.asset_id.values}, geometry=g.to_crs(UTM).representative_point().values,
                                   crs=UTM)
            hit = gpd.sjoin(pts, c, predicate="within").drop_duplicates("asset_id")
            for aid, cid in zip(hit.asset_id, hit.catchment_id):
                add_edge(G, "LOCATED_WITHIN", aid, cid, rule="point inside the simulated catchment polygon",
                         data_status="simulated", confidence="med")
    return G


# ---- queries -----------------------------------------------------------------------------------------------
def _edge_dict(u: str, v: str, d: dict) -> dict:
    return {"source": u, "target": v, **d}


def node_dict(G: nx.MultiDiGraph, n: str) -> dict:
    return {"id": n, **G.nodes[n]}


def neighbors(G: nx.MultiDiGraph, nid: str, depth: int = 1, types: set[str] | None = None,
              max_nodes: int = 250) -> dict:
    """k-hop neighbourhood ignoring direction, optionally restricted to edge types; capped at max_nodes."""
    if nid not in G:
        raise KeyError(nid)
    seen, edges, q, truncated = {nid: 0}, {}, deque([nid]), False
    while q:
        u = q.popleft()
        if seen[u] >= depth:
            continue
        for a, b, d in list(G.out_edges(u, data=True)) + list(G.in_edges(u, data=True)):
            if types and d["type"] not in types:
                continue
            w = b if a == u else a
            if w not in seen:
                if len(seen) >= max_nodes:
                    truncated = True
                    continue
                seen[w] = seen[u] + 1
                q.append(w)
            edges[d["relationship_id"]] = _edge_dict(a, b, d)
    return {"center": nid, "depth": depth, "truncated": truncated,
            "nodes": [{**node_dict(G, n), "hop": h} for n, h in seen.items()],
            "edges": [e for e in edges.values() if e["source"] in seen and e["target"] in seen]}


def _drains_to(G: nx.MultiDiGraph) -> nx.DiGraph:
    return nx.DiGraph((u, v) for u, v, k in G.edges(keys=True) if k == "DRAINS_TO")


def upstream(G: nx.MultiDiGraph, drain_id: str) -> set[str]:
    T = _drains_to(G)
    return nx.ancestors(T, drain_id) if drain_id in T else set()


def downstream(G: nx.MultiDiGraph, drain_id: str) -> list[str]:
    """Ordered flow path from the drain to its outfall."""
    T, path, cur = _drains_to(G), [], drain_id
    while cur in T and T.out_degree(cur):
        cur = next(iter(T.successors(cur)))
        path.append(cur)
    return path


def path(G: nx.MultiDiGraph, src: str, dst: str) -> dict:
    U = nx.Graph(G.to_undirected(as_view=True))
    nodes = nx.shortest_path(U, src, dst)
    edges = []
    for a, b in zip(nodes, nodes[1:]):
        if G.has_edge(a, b):
            d = next(iter(G[a][b].values()))
            edges.append(_edge_dict(a, b, d))
        else:
            d = next(iter(G[b][a].values()))
            edges.append(_edge_dict(b, a, d))
    return {"nodes": [node_dict(G, n) for n in nodes], "edges": edges, "hops": len(edges)}


def relationships_of(G: nx.MultiDiGraph, nid: str) -> list[dict]:
    if nid not in G:
        return []
    out = []
    for direction, it in (("out", G.out_edges(nid, data=True)), ("in", G.in_edges(nid, data=True))):
        for a, b, d in it:
            other = b if direction == "out" else a
            o = G.nodes[other]
            out.append({**d, "direction": direction, "other_id": other, "other_kind": o.get("kind"),
                        "other_type": o.get("asset_type"), "other_name": o.get("name"),
                        "label": EDGE_TYPES[d["type"]]["label"] if direction == "out" else
                        f"← {EDGE_TYPES[d['type']]['label']}"})
    return out


def summary(G: nx.MultiDiGraph) -> dict:
    kinds = Counter(d["kind"] for _, d in G.nodes(data=True))
    etypes = Counter(k for _, _, k in G.edges(keys=True))
    status = Counter(d["data_status"] for _, _, d in G.edges(data=True))
    return {
        "nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
        "node_kinds": dict(kinds), "edge_types": dict(etypes), "edge_data_status": dict(status),
        "components": nx.number_weakly_connected_components(G),
        "isolated_nodes": sum(1 for n in G if G.degree(n) == 0),
        "registry": EDGE_TYPES,
    }
