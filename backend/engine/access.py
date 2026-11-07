"""P12 travel-time accessibility (free-flow, not live traffic) and how a flood scenario degrades it.

Times are building-node → nearest facility-node along the directed drive graph (pilot + 2 km buffer).
Scenario: impassable roads removed, impaired roads at half speed. No path → None ("isolated"), never 0.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

import networkx as nx
import numpy as np

CATEGORIES = {"hospital": {"hospital"}, "fire": {"fire_station"}, "metro": {"metro_station", "rail_station"}}
LABEL = "Free-flow travel time estimate (OSM speeds / assumed class speeds) — not live traffic"
IMPAIRED_FACTOR = 2.0  # impaired road: speed × 0.5


@dataclass
class AccessContext:
    G: nx.DiGraph
    road_edges: dict[str, list[tuple[int, int]]]
    building_nodes: dict[str, int]
    facilities: dict[str, dict]
    node_xy: np.ndarray
    node_ids: np.ndarray
    baseline: dict[str, dict] = field(default_factory=dict)


def load_context(path: Path) -> AccessContext:
    d = json.loads(path.read_text(encoding="utf-8"))
    G = nx.DiGraph()
    road_edges: dict[str, list[tuple[int, int]]] = {}
    for u, v, length, tt, hw, rid in d["edges"]:
        if not G.has_edge(u, v) or G[u][v]["tt"] > tt:  # parallel edges: keep the fastest
            G.add_edge(u, v, tt=tt, length=length, road=rid)
        if rid:
            road_edges.setdefault(rid, []).append((u, v))
    ids = np.array([n[0] for n in d["nodes"]])
    xy = np.array([[n[1], n[2]] for n in d["nodes"]])
    ctx = AccessContext(G, road_edges, d["building_nodes"], d["facilities"], xy, ids)
    ctx.baseline = compute(ctx)
    return ctx


def nearest_node(ctx: AccessContext, lon: float, lat: float) -> int:
    dx = (ctx.node_xy[:, 0] - lon) * math.cos(math.radians(lat))
    return int(ctx.node_ids[np.argmin(dx * dx + (ctx.node_xy[:, 1] - lat) ** 2)])


def _sources(ctx: AccessContext, cat: str) -> dict[int, str]:
    return {f["node"]: fid for fid, f in ctx.facilities.items() if f["type"] in CATEGORIES[cat]}


def _graph(ctx: AccessContext, removed: set[str], slowed: set[str]) -> nx.DiGraph:
    if not removed and not slowed:
        return ctx.G
    H = ctx.G.copy()
    for rid in removed:
        H.remove_edges_from([e for e in ctx.road_edges.get(rid, []) if H.has_edge(*e)])
    for rid in slowed - removed:
        for u, v in ctx.road_edges.get(rid, []):
            if H.has_edge(u, v):
                H[u][v]["tt"] *= IMPAIRED_FACTOR
    return H


def compute(ctx: AccessContext, removed: set[str] | None = None, slowed: set[str] | None = None) -> dict[str, dict]:
    """Per category: {building_id: {'min': minutes | None, 'to': facility_id | None}} plus node minutes."""
    H = _graph(ctx, removed or set(), slowed or set())
    R = H.reverse(copy=False)
    out = {}
    for cat in CATEGORIES:
        src = _sources(ctx, cat)
        dist, paths = nx.multi_source_dijkstra(R, set(src), weight="tt") if src else ({}, {})
        node_min = {n: (dist[n] / 60, src[paths[n][0]]) for n in dist}
        out[cat] = {"buildings": {b: {"min": round(node_min[n][0], 2) if n in node_min else None,
                                      "to": node_min[n][1] if n in node_min else None}
                                  for b, n in ctx.building_nodes.items()},
                    "nodes": node_min}
    return out


def stats(per_building: dict[str, dict]) -> dict:
    vals = [v["min"] for v in per_building.values() if v["min"] is not None]
    vals_sorted = sorted(vals)
    return {"n": len(per_building), "isolated": sum(v["min"] is None for v in per_building.values()),
            "median_min": round(median(vals), 2) if vals else None,
            "p90_min": round(vals_sorted[int(0.9 * (len(vals_sorted) - 1))], 2) if vals else None,
            "max_min": round(max(vals), 2) if vals else None}


def minutes_from(ctx: AccessContext, result: dict, cat: str, node: int) -> float | None:
    v = result[cat]["nodes"].get(node)
    return round(v[0], 2) if v else None


def scenario(ctx: AccessContext, flood: dict) -> dict:
    """Δ accessibility under a flood result (impassable removed, impaired slowed)."""
    roads = flood["layers"]["roads"]
    removed = {r for r, v in roads.items() if v["state"] == "impassable"}
    slowed = {r for r, v in roads.items() if v["state"] == "impaired"}
    sc = compute(ctx, removed, slowed)
    out = {"removed_roads": len(removed), "slowed_roads": len(slowed), "categories": {}, "scenario": sc}
    for cat in CATEGORIES:
        b0, b1 = ctx.baseline[cat]["buildings"], sc[cat]["buildings"]
        deltas = {b: round(b1[b]["min"] - b0[b]["min"], 2) for b in b0
                  if b0[b]["min"] is not None and b1[b]["min"] is not None}
        newly = [b for b in b0 if b0[b]["min"] is not None and b1[b]["min"] is None]
        longer = {b: d for b, d in deltas.items() if d > 0.05}
        out["categories"][cat] = {
            "baseline": stats(b0), "scenario": stats(b1), "newly_isolated": len(newly),
            "buildings_slower": len(longer), "mean_delta_min": round(sum(longer.values()) / len(longer), 2) if longer else 0.0,
            "max_delta_min": round(max(longer.values()), 2) if longer else 0.0,
        }
    # facilities inside the pilot that can no longer reach any hospital
    cut = []
    for fid, f in ctx.facilities.items():
        if f["in_pilot"] and f["type"] not in CATEGORIES["hospital"]:
            if minutes_from(ctx, ctx.baseline, "hospital", f["node"]) is not None and \
                    minutes_from(ctx, sc, "hospital", f["node"]) is None:
                cut.append({"asset_id": fid, "name": f["name"], "type": f["type"]})
    out["facilities_no_hospital_route"] = cut
    return out


def road_block_step(ctx: AccessContext, rid: str, sc: dict) -> dict | None:
    """Access hop for a flooded road's Why? chain: buildings next to it, nearest-hospital time before → after."""
    ends = {n for e in ctx.road_edges.get(rid, []) for n in e}
    blds = [b for b, n in ctx.building_nodes.items() if n in ends]
    if not blds:
        return None
    b0, b1 = ctx.baseline["hospital"]["buildings"], sc["hospital"]["buildings"]
    before = [b0[b]["min"] for b in blds if b0[b]["min"] is not None]
    after = [b1[b]["min"] for b in blds]
    iso = sum(a is None for a in after)
    aft = [a for a in after if a is not None]
    if not before:
        return None
    mb, ma = sum(before) / len(before), (sum(aft) / len(aft) if aft else None)
    label = (f"{len(blds)} building(s) beside this road: nearest hospital {mb:.1f} → "
             + (f"{ma:.1f} min" if ma is not None else "no route") + (f" ({iso} isolated)" if iso and aft else "")
             + " (free-flow)")
    return {"from": rid, "edge": "ACCESSIBLE_VIA → hospital route", "to": "hospital access",
            "rule": "impassable roads removed, impaired at half speed; multi-source Dijkstra to the nearest hospital",
            "label": label, "formula": "Δt = t_scenario − t_baseline",
            "values": {"buildings": len(blds), "before_min": round(mb, 2),
                       "after_min": None if ma is None else round(ma, 2), "isolated": iso}}
