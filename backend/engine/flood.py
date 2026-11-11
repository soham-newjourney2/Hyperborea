"""P08 extreme-rainfall cascade (planning §7). Runs on a scenario overlay — never mutates the baseline.

rain → catchment runoff (rational) → drain routing on DRAINS_TO (capacity, overflow) → ponding per catchment →
roads (impaired / impassable) → buildings (above plinth) → facilities (all access roads impassable).
Every affected asset gets a risk INDEX (not a probability) and an explanation chain with the numbers.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone

import geopandas as gpd
import networkx as nx

from .hydraulics import rational_runoff
from .rules import flood_rules, risk_rules
from ..app.core.regions import metric_crs as utm  # P16: active region's UTM zone (Sector V = 32645)

LABEL = "Scenario-based estimate — not a prediction"
DATA_STATUS = "modelled (simulated inputs)"


def _attrs(s):
    return json.loads(s) if isinstance(s, str) else (s or {})


@dataclass
class FloodContext:
    """Read-only, precomputed view of the baseline used by every run."""
    order: list[str]
    drain: dict[str, dict]
    up: dict[str, list[str]]
    cat: dict[str, dict]
    road: dict[str, dict]
    road_cats: dict[str, set[str]]
    bld: dict[str, dict]
    fac: dict[str, dict]
    upstream_n: dict[str, int] = field(default_factory=dict)
    trf: dict[str, dict] = field(default_factory=dict)  # P10 simulated transformers


def build_context(layers: dict[str, gpd.GeoDataFrame], G: nx.MultiDiGraph) -> FloodContext:
    dr = layers["drains"]
    drain = {}
    for aid, a in zip(dr.asset_id, dr["attrs"].map(_attrs)):
        drain[aid] = {k: a.get(k) for k in ("capacity_m3s", "condition_factor", "catchment_id", "drains_to", "road_id",
                                            "diameter_m", "slope", "manning_n", "length_m", "upstream_ca_m2",
                                            "upstream_area_m2", "road_class", "n_upstream")}
    T = nx.DiGraph()
    T.add_nodes_from(drain)
    T.add_edges_from((d, v["drains_to"]) for d, v in drain.items() if v["drains_to"] in drain)
    order = list(nx.topological_sort(T))
    up = {d: list(T.predecessors(d)) for d in drain}

    ct = layers["catchments"]
    cat = {aid: {"area_m2": a["area_m2"], "runoff_c": a["runoff_c"], "drain_id": a["drain_id"]}
           for aid, a in zip(ct.asset_id, ct["attrs"].map(_attrs))}

    # Roads: catchments that can flood them = adjacent drains' catchments + catchment(s) the road crosses.
    rd = layers["roads"]
    rd = rd[rd["in_pilot"].astype(bool)]
    road = {aid: {"name": nm if isinstance(nm, str) else None, "highway": a.get("highway"),
                  "length_m": a.get("length_m", 0.0)}
            for aid, nm, a in zip(rd.asset_id, rd["name"], rd["attrs"].map(_attrs))}
    road_cats: dict[str, set[str]] = {r: set() for r in road}
    for d, v in drain.items():
        if v["road_id"] in road_cats and v["catchment_id"] in cat:
            road_cats[v["road_id"]].add(v["catchment_id"])
    mids = gpd.GeoDataFrame({"rid": rd.asset_id.values},
                            geometry=rd.to_crs(utm()).geometry.interpolate(0.5, normalized=True).values, crs=utm())
    hit = gpd.sjoin(mids, ct[["asset_id", "geometry"]].to_crs(utm()), predicate="within")
    for rid, cid in zip(hit.rid, hit.asset_id):
        road_cats[rid].add(cid)

    bld = {}
    for n, d in G.nodes(data=True):
        if d.get("kind") == "building":
            cats = [v for _, v, k in G.out_edges(n, keys=True) if k == "LOCATED_WITHIN"]
            if cats:
                bld[n] = {"catchment_id": cats[0], "name": d.get("name")}
    bl = layers["buildings"]
    for aid, a in zip(bl.asset_id, bl["attrs"].map(_attrs)):
        if aid in bld:
            bld[aid].update(levels=a.get("levels"), area_m2=a.get("area_m2"), height_status=a.get("height_status"))

    fac = {}
    for n, d in G.nodes(data=True):
        if d.get("kind") == "facility":
            dep = [v for _, v, k in G.out_edges(n, keys=True) if k == "DEPENDS_ON"]
            fac[n] = {"type": d.get("asset_type"), "name": d.get("name"),
                      "roads": [v for v in dep if G.nodes[v].get("kind") == "road"],
                      "transformers": [v for v in dep if G.nodes[v].get("kind") == "transformer"]}
    upstream_n = {d: int(v.get("n_upstream") or 0) for d, v in drain.items()}
    trf = {}
    tl = layers.get("transformers")
    if tl is not None and not tl.empty:
        for aid, nm, a in zip(tl.asset_id, tl["name"], tl["attrs"].map(_attrs)):
            cats = [v for _, v, k in G.out_edges(aid, keys=True) if k == "LOCATED_WITHIN"] if aid in G else []
            trf[aid] = {"name": nm, "catchment_id": cats[0] if cats else None, "plinth_m": a.get("plinth_m", 0.6),
                        "rating_kva": a.get("rating_kva"), "load_kva": a.get("load_kva"),
                        "buildings": a.get("buildings", []), "facilities": a.get("facilities", [])}
    return FloodContext(order, drain, up, cat, road, road_cats, bld, fac, upstream_n, trf)


# ---- one run ---------------------------------------------------------------------------------------------
def params_id(p: dict) -> str:
    return hashlib.sha1(json.dumps(p, sort_keys=True).encode()).hexdigest()[:12]


def _risk(components: dict[str, float]) -> dict:
    rr = risk_rules()
    w, fl = rr["weights"], rr["floor"]
    comp = {k: round(min(max(v, fl), 1.0), 3) for k, v in components.items()}
    idx = math.prod(comp[k] ** w[k] for k in w)
    return {"index": round(idx, 3), "components": comp, "weights": w,
            "formula": "R = H^wH · E^wE · V^wV · C^wC", "label": "risk index (0–1), not a probability"}


def road_class(h) -> str:
    h = str(h or "")
    if any(k in h for k in ("trunk", "primary")):
        return "arterial"
    if any(k in h for k in ("secondary", "tertiary")):
        return "secondary"
    return "local"


def run_flood(ctx: FloodContext, params: dict, overlay: dict | None = None) -> dict:
    """overlay (scenario only): {'extra_inflow': {drain: m³/s}, 'capacity': {drain: full-flow m³/s}} (P09);
    P23: {'plinth': {transformer: m}} raised plinths, {'storage_m3': {catchment: m³}} detention holding overflow."""
    extra = (overlay or {}).get("extra_inflow", {})
    cap_override = (overlay or {}).get("capacity", {})
    plinth_override = (overlay or {}).get("plinth", {})
    storage = (overlay or {}).get("storage_m3", {})
    fr, rr = flood_rules(), risk_rules()
    rain, dur, scale = float(params["rain_mm_h"]), float(params["duration_h"]), float(params.get("condition_scale", 1.0))
    secs = dur * 3600
    frac, dmax = fr["ponding"]["low_lying_fraction"], fr["ponding"]["max_depth_m"]
    imp, impass, plinth = fr["roads"]["impaired_m"], fr["roads"]["impassable_m"], fr["buildings"]["plinth_m"]
    near = fr["drains"]["near_capacity_ratio"]

    # 1–2: runoff + routing in topological order (scenario values only; baseline dicts are read-only)
    D, outflow = {}, {}
    for d in ctx.order:
        v = ctx.drain[d]
        c = ctx.cat.get(v["catchment_id"])
        q_local = max((rational_runoff(c["runoff_c"], rain, c["area_m2"]) if c else 0.0) + extra.get(d, 0.0), 0.0)
        q_up = sum(outflow[u] for u in ctx.up[d])
        q_in = q_local + q_up
        cond = min(max(v["condition_factor"] * scale, 0.05), 1.0)
        cap = cap_override.get(d, v["capacity_m3s"]) * cond
        q_out = min(q_in, cap)
        over = q_in - q_out
        outflow[d] = q_out
        ratio = q_in / cap if cap > 0 else math.inf
        D[d] = {"q_local": round(q_local, 4), "q_upstream": round(q_up, 4), "q_in": round(q_in, 4),
                "capacity": round(cap, 4), "condition": round(cond, 3), "q_out": round(q_out, 4),
                "overflow_m3s": round(over, 4), "load_ratio": round(ratio, 3),
                "state": "overloaded" if over > 1e-9 else "near" if ratio >= near else "ok"}

    # 3: ponding — each drain's overflow pools in its own catchment's low-lying fraction
    C = {}
    for d, r in D.items():
        cid = ctx.drain[d]["catchment_id"]
        if r["overflow_m3s"] > 0 and cid in ctx.cat:
            vol = max(r["overflow_m3s"] * secs - storage.get(cid, 0.0), 0.0)  # P23: detention tank captures overflow first
            if vol <= 0:
                continue
            raw = vol / (ctx.cat[cid]["area_m2"] * frac)
            C[cid] = {"overflow_m3": round(vol, 1), "depth_m": round(min(raw, dmax), 3), "capped": raw > dmax,
                      "drain_id": d}

    # 4: roads
    R = {}
    for rid, cats in ctx.road_cats.items():
        wet = [(C[c]["depth_m"], c) for c in cats if c in C]
        if not wet:
            continue
        depth, cid = max(wet)
        if depth >= imp:
            R[rid] = {"depth_m": depth, "state": "impassable" if depth >= impass else "impaired", "via": cid}

    # 5: buildings above plinth
    B = {bid: {"depth_m": C[b["catchment_id"]]["depth_m"], "via": b["catchment_id"]}
         for bid, b in ctx.bld.items() if b["catchment_id"] in C and C[b["catchment_id"]]["depth_m"] >= plinth}

    # 5b (P10): transformers standing in water >= plinth -> protective shutdown -> supplied buildings lose power
    TS = {}
    for tid, t in ctx.trf.items():
        c = C.get(t["catchment_id"])
        if c and c["depth_m"] >= plinth_override.get(tid, t["plinth_m"]):
            TS[tid] = {"depth_m": c["depth_m"], "via": t["catchment_id"], "state": "shutdown",
                       "buildings": len(t["buildings"]), "facilities": t["facilities"]}
    BP = {b: tid for tid in TS for b in ctx.trf[tid]["buildings"]}

    # 6: facilities — access via DEPENDS_ON roads (pilot roads only) + power via DEPENDS_ON transformer
    F = {}
    for fid, f in ctx.fac.items():
        modelled = [r for r in f["roads"] if r in ctx.road_cats]
        bad = [r for r in modelled if R.get(r, {}).get("state") == "impassable"]
        slow = [r for r in modelled if R.get(r, {}).get("state") == "impaired"]
        access = ("not_assessed" if not modelled else "access_cut" if len(bad) == len(modelled)
                  else "access_impaired" if bad or slow else "ok")
        lost = [t for t in f.get("transformers", []) if t in TS]
        power = "loss" if lost else ("ok" if f.get("transformers") else "not_modelled")
        if power == "loss" or access in ("access_cut", "access_impaired"):
            F[fid] = {"state": "power_loss" if lost else access, "access": access, "power": power,
                      "backup_power": "unknown", "transformers_shutdown": lost,
                      "roads_impassable": bad, "roads_impaired": slow, "roads_modelled": modelled}

    # 7–8: risk + explanations
    rain_src = params.get("preset_source_id", "syn_rain")
    affected, explain = [], {}

    def drain_steps(d: str) -> list[dict]:
        v, r = ctx.drain[d], D[d]
        demand = rational_runoff(1.0, rain, v.get("upstream_ca_m2") or 0)
        return [
            {"from": "rain", "edge": "runoff", "to": d, "rule": "rational method on the drain's own + upstream catchments",
             "label": f"{rain:g} mm/h on ΣC·A = {v.get('upstream_ca_m2', 0):,.0f} m² upstream "
                      f"({ctx.upstream_n.get(d, 0)} drains) → demand {demand:.2f} m³/s",
             "formula": "Q = C · i · A / 3.6e6", "values": {"rain_mm_h": rain, "upstream_ca_m2": v.get("upstream_ca_m2"),
                                                           "demand_m3s": round(demand, 3)}},
            {"from": d, "edge": "capacity", "to": d,
             "rule": "Manning full flow × condition (simulated drain)",
             "label": f"inflow {r['q_in']:.2f} m³/s (local {r['q_local']:.3f} + upstream {r['q_upstream']:.2f}, "
                      f"already capped upstream) vs capacity {r['capacity']:.2f} m³/s "
                      f"(d {v['diameter_m']} m, S {v['slope']}, condition {r['condition']}) → overflow {r['overflow_m3s']:.2f} m³/s",
             "formula": "Q = (1/n)·A·R^(2/3)·S^(1/2) × condition", "values": {k: r[k] for k in ("q_in", "capacity", "overflow_m3s", "load_ratio")}},
        ]

    def pond_step(cid: str) -> dict:
        c, a = C[cid], ctx.cat[cid]
        return {"from": c["drain_id"], "edge": "overflow → ponding", "to": cid,
                "rule": f"overflow volume pools on {frac:.0%} of the catchment (capped {dmax} m)",
                "label": f"{c['overflow_m3']:,.0f} m³ over {dur:g} h on {frac:.0%} of {a['area_m2']:,.0f} m² → "
                         f"{c['depth_m']:.2f} m{' (capped)' if c['capped'] else ''}",
                "formula": "depth = overflow × duration / (area × 0.3)", "values": {"overflow_m3": c["overflow_m3"], "depth_m": c["depth_m"]}}

    common = {
        "inputs": [{"name": "rain", "value": rain, "unit": "mm/h", "source_id": rain_src, "data_status": "simulated"},
                   {"name": "duration", "value": dur, "unit": "h", "source_id": rain_src, "data_status": "simulated"},
                   {"name": "condition scale", "value": scale, "unit": "×", "source_id": "syn_drain", "data_status": "simulated"},
                   {"name": "drain network", "value": "P06", "unit": "", "source_id": "syn_drain", "data_status": "simulated"},
                   {"name": "catchment runoff C", "value": "roof/road/other", "unit": "", "source_id": "syn_drain", "data_status": "modelled"}],
        "assumptions": fr["assumptions"], "data_status": DATA_STATUS, "confidence": "low",
        "improve": ["Municipal drain survey (sizes, invert levels, condition)", "Pumping-station capacities and outfall levels",
                    "LiDAR / survey-grade DEM (Copernicus DSM error ~2–4 m)", "Observed waterlogging reports to calibrate depths"],
    }

    for d, r in D.items():
        if r["state"] != "overloaded":
            continue
        v = ctx.drain[d]
        risk = _risk({"hazard": min(r["load_ratio"] / 3, 1), "exposure": 1.0,
                      "vulnerability": 1 - r["condition"] + 0.2, "consequence": min((v.get("upstream_area_m2") or 0) / 5e5, 1)})
        affected.append({"asset_id": d, "kind": "drain", "name": None, "state": "overloaded", "risk": risk["index"],
                         "detail": f"load {r['load_ratio']:.1f}× capacity"})
        explain[d] = {"asset_id": d, "kind": "drain", "state": "overloaded",
                      "trigger": f"inflow {r['q_in']:.2f} m³/s > capacity {r['capacity']:.2f} m³/s",
                      "path": drain_steps(d) + ([pond_step(v["catchment_id"])] if v["catchment_id"] in C else []),
                      "risk": risk, "mitigation": ["Desilt / clean this drain (raises condition factor)",
                                                   "Upsize or add a relief drain toward the outfall"], **common}

    for rid, r in R.items():
        c = C[r["via"]]
        info = ctx.road[rid]
        cls = road_class(info["highway"])
        risk = _risk({"hazard": r["depth_m"] / dmax, "exposure": 1.0 if r["state"] == "impassable" else r["depth_m"] / impass,
                      "vulnerability": rr["vulnerability"]["road_arterial" if cls == "arterial" else "road_local"],
                      "consequence": rr["consequence"][f"road_{cls}"]})
        affected.append({"asset_id": rid, "kind": "road", "name": info["name"], "state": r["state"], "risk": risk["index"],
                         "detail": f"{r['depth_m']:.2f} m water"})
        explain[rid] = {"asset_id": rid, "kind": "road", "state": r["state"],
                        "trigger": f"ponding {r['depth_m']:.2f} m ≥ {'impassable' if r['state'] == 'impassable' else 'impaired'} "
                                   f"threshold {impass if r['state'] == 'impassable' else imp} m",
                        "path": drain_steps(c["drain_id"]) + [pond_step(r["via"]), {
                            "from": r["via"], "edge": "ADJACENT_TO / crosses", "to": rid,
                            "rule": f"impaired ≥ {imp} m, impassable ≥ {impass} m (config/flood.yaml)",
                            "label": f"road under {r['depth_m']:.2f} m → {r['state']}", "formula": "threshold",
                            "values": {"depth_m": r["depth_m"]}}],
                        "risk": risk, "mitigation": ["Pre-position pumps / divert traffic", "Raise road crown or add inlets"],
                        **common}

    for bid, b in B.items():
        info = ctx.bld[bid]
        c = C[b["via"]]
        lv = info.get("levels") or 1
        risk = _risk({"hazard": b["depth_m"] / dmax, "exposure": min(b["depth_m"] / plinth, 1),
                      "vulnerability": rr["vulnerability"]["building_low_rise" if lv <= 2 else "building_mid_rise"],
                      "consequence": min((info.get("area_m2") or 0) * lv / 5000, 1)})
        affected.append({"asset_id": bid, "kind": "building", "name": info.get("name"), "state": "above_plinth",
                         "risk": risk["index"], "detail": f"{b['depth_m']:.2f} m vs plinth {plinth} m"})
        explain[bid] = {"asset_id": bid, "kind": "building", "state": "above_plinth",
                        "trigger": f"ponding {b['depth_m']:.2f} m ≥ plinth {plinth} m",
                        "path": drain_steps(c["drain_id"]) + [pond_step(b["via"]), {
                            "from": b["via"], "edge": "LOCATED_WITHIN", "to": bid, "rule": f"plinth {plinth} m (assumed)",
                            "label": f"water {b['depth_m']:.2f} m above ground > plinth {plinth} m → ground floor exposed",
                            "formula": "depth ≥ plinth", "values": {"depth_m": b["depth_m"]}}],
                        "risk": risk, "mitigation": ["Flood barriers / raise thresholds", "Move ground-floor assets"], **common}

    for tid, t in TS.items():
        info = ctx.trf[tid]
        c = C[t["via"]]
        risk = _risk({"hazard": t["depth_m"] / dmax, "exposure": 1.0, "vulnerability": 0.7,
                      "consequence": min(len(info["buildings"]) / 40 + 0.3 * bool(info["facilities"]), 1)})
        affected.append({"asset_id": tid, "kind": "transformer", "name": info["name"], "state": "shutdown",
                         "risk": risk["index"], "detail": f"{t['depth_m']:.2f} m ≥ plinth {info['plinth_m']} m · "
                                                         f"{len(info['buildings'])} buildings off"})
        explain[tid] = {"asset_id": tid, "kind": "transformer", "state": "shutdown",
                        "trigger": f"ponding {t['depth_m']:.2f} m ≥ transformer plinth {info['plinth_m']} m",
                        "path": drain_steps(c["drain_id"]) + [pond_step(t["via"]), {
                            "from": t["via"], "edge": "LOCATED_WITHIN", "to": tid,
                            "rule": f"protective shutdown when water ≥ plinth {info['plinth_m']} m (config/flood.yaml, assumed)",
                            "label": f"transformer ({info['rating_kva']} kVA, {len(info['buildings'])} buildings) under "
                                     f"{t['depth_m']:.2f} m → protective shutdown", "formula": "depth ≥ plinth",
                            "values": {"depth_m": t["depth_m"], "plinth_m": info["plinth_m"]}}],
                        "risk": risk, "mitigation": ["Raise transformer plinth above 1 m", "Mobile substation / genset on standby"],
                        **common}

    for fid, f in F.items():
        info = ctx.fac[fid]
        parts, chains = [], []
        if f["power"] == "loss":
            tid = f["transformers_shutdown"][0]
            parts.append("power lost (transformer shut down; backup power unknown)")
            chains.append(("power", explain[tid]["path"] + [{
                "from": tid, "edge": "SUPPLIES / DEPENDS_ON", "to": fid,
                "rule": "facility is supplied by this transformer; backup generator / UPS not mapped",
                "label": "supplying transformer off → facility loses grid power · backup power: UNKNOWN",
                "formula": "supplier shutdown ⇒ power loss", "values": {"transformer": tid, "backup_power": "unknown"}}]))
        if f["access"] in ("access_cut", "access_impaired"):
            road_hits = f["roads_impassable"] + f["roads_impaired"]
            worst_id = max(road_hits, key=lambda r: R[r]["depth_m"])
            lbl = ("all access roads impassable → access cut" if f["access"] == "access_cut" else
                   f"{len(f['roads_impassable'])} impassable + {len(f['roads_impaired'])} impaired of "
                   f"{len(f['roads_modelled'])} access roads")
            parts.append(lbl)
            chains.append(("access", explain[worst_id]["path"] + [{
                "from": worst_id, "edge": "DEPENDS_ON", "to": fid,
                "rule": "facility needs its access roads (≤ 50 m, up to 3); all impassable → cut", "label": lbl,
                "formula": "count impassable / modelled access roads",
                "values": {"impassable": len(f["roads_impassable"]), "impaired": len(f["roads_impaired"]),
                           "modelled": len(f["roads_modelled"])}}]))
        depth = max([R[r]["depth_m"] for r in f["roads_impassable"] + f["roads_impaired"]]
                    + [TS[t]["depth_m"] for t in f["transformers_shutdown"]])
        share = len(f["roads_impassable"]) / len(f["roads_modelled"]) if f["roads_modelled"] else 0
        risk = _risk({"hazard": depth / dmax,
                      "exposure": 1.0 if f["power"] == "loss" else max(share, 0.3 if f["roads_impaired"] else 0),
                      "vulnerability": rr["vulnerability"]["facility"],
                      "consequence": rr["consequence"].get(info["type"], 0.5)})
        label = " + ".join(parts)
        affected.append({"asset_id": fid, "kind": "facility", "name": info["name"], "state": f["state"],
                         "risk": risk["index"], "detail": label})
        explain[fid] = {"asset_id": fid, "kind": "facility", "state": f["state"], "trigger": label,
                        "path": chains[0][1], "also": [{"title": k, "path": p} for k, p in chains[1:]],
                        "risk": risk, "mitigation": ["Verify / test backup generator and fuel (backup status unknown)",
                                                     "Pre-plan alternative ambulance/fire routes (P12)",
                                                     "Priority pumping on access roads"], **common}

    affected.sort(key=lambda a: (-a["risk"], a["kind"], a["asset_id"]))
    km = lambda st: round(sum(ctx.road[r]["length_m"] for r, v in R.items() if v["state"] == st) / 1000, 2)  # noqa: E731
    summary = {
        "drains_overloaded": sum(r["state"] == "overloaded" for r in D.values()),
        "drains_near_capacity": sum(r["state"] == "near" for r in D.values()),
        "drains_total": len(D),
        "catchments_ponded": len(C),
        "max_depth_m": max((c["depth_m"] for c in C.values()), default=0.0),
        "total_overflow_m3": round(sum(c["overflow_m3"] for c in C.values()), 0),
        "roads_impaired": sum(v["state"] == "impaired" for v in R.values()),
        "roads_impassable": sum(v["state"] == "impassable" for v in R.values()),
        "road_km_impaired": km("impaired"), "road_km_impassable": km("impassable"),
        "buildings_exposed": len(B),
        "facilities_access_cut": sum(f["state"] == "access_cut" for f in F.values()),
        "facilities_access_impaired": sum(f["state"] == "access_impaired" for f in F.values()),
        "facilities_affected": len(F),
        "transformers_shutdown": len(TS),
        "buildings_power_loss": len(BP),
        "facilities_power_loss": sum(f["power"] == "loss" for f in F.values()),
    }
    return {
        "result_id": params_id(params), "params": params, "label": LABEL, "data_status": DATA_STATUS,
        "summary": summary,
        "layers": {"drains": D, "roads": R, "catchments": C, "buildings": B, "facilities": F,
                   "transformers": TS, "buildings_power": BP},
        "affected": affected, "explanations": explain,
        "assumptions": fr["assumptions"], "rules": {"flood": fr, "risk": rr},
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


class ResultCache:
    """Small LRU of results by params hash (deterministic inputs → same result)."""

    def __init__(self, size: int = 16):
        self.size, self.data = size, OrderedDict()

    def get_or_run(self, ctx: FloodContext, params: dict) -> dict:
        rid = params_id(params)
        if rid in self.data:
            self.data.move_to_end(rid)
            return self.data[rid]
        res = run_flood(ctx, params)
        self.data[rid] = res
        if len(self.data) > self.size:
            self.data.popitem(last=False)
        return res
