"""P23 upgrade optimiser: which interventions remove the most cascade risk per unit of (assumed) cost, within a budget.

Candidates come from the scenario's own failures: overloaded drains (one pipe size up), shut-down transformers (raise the
plinth), ponded catchments (detention tank sized to the overflow). Lazy greedy on gain / cost with re-evaluation, so
interactions (an upsized drain pushing water downstream) are captured. Every run is the full rule engine on an overlay.
"""
from __future__ import annotations

import heapq
import math

from .flood import FloodContext, run_flood
from .hydraulics import manning_full_circular, next_pipe_size

LABEL = ("Screening optimiser — assumed unit costs and value weights, simulated networks; ranks options, "
         "not an engineering design or budget")


def objective(summary: dict, weights: dict) -> float:
    return round(sum(w * float(summary.get(k) or 0) for k, w in weights.items()), 2)


def _merge(base: dict, add: dict) -> dict:
    out = {k: dict(v) for k, v in base.items()}
    for k, v in add.items():
        out.setdefault(k, {}).update(v)
    return out


def candidates(ctx: FloodContext, res: dict, cfg: dict, cur: dict) -> list[dict]:
    out = []
    for d, v in res["layers"]["drains"].items():
        if v.get("state") != "overloaded":
            continue
        dr = ctx.drain[d]
        new_d = next_pipe_size(dr["diameter_m"], 1)
        if new_d <= dr["diameter_m"]:
            continue
        cost = dr["length_m"] * cur["drain_upsize_per_m"]
        out.append({"kind": "drain_upsize", "asset_id": d, "cost": round(cost),
                    "label": f"Upsize drain {dr['diameter_m']:.2f} → {new_d:.2f} m ({dr['length_m']:.0f} m)",
                    "overlay": {"capacity": {d: manning_full_circular(new_d, dr["slope"], dr["manning_n"])}}})
    for t, v in res["layers"].get("transformers", {}).items():
        if v.get("state") != "shutdown":
            continue
        out.append({"kind": "plinth_raise", "asset_id": t, "cost": round(cur["plinth_raise_per_transformer"]),
                    "label": f"Raise transformer plinth to {cfg['plinth_raise_to_m']} m ({ctx.trf[t]['name'] or t})",
                    "overlay": {"plinth": {t: float(cfg["plinth_raise_to_m"])}}})
    for c, v in res["layers"]["catchments"].items():
        vol = float(v.get("overflow_m3") or 0)
        if vol <= 0:
            continue
        tank = min(math.ceil(vol / 50) * 50, cfg["detention_max_tank_m3"])
        out.append({"kind": "detention", "asset_id": c, "cost": round(tank * cur["detention_per_m3"]),
                    "label": f"Detention tank {tank:,.0f} m³ in catchment {c.split('_')[-2] if '_' in c else c}",
                    "overlay": {"storage_m3": {c: float(tank)}}, "tank_m3": tank})
    return out


def optimise(ctx: FloodContext, params: dict, budget: float, cfg: dict, cur: dict) -> dict:
    w = cfg["objective"]
    base = run_flood(ctx, params)
    obj0 = objective(base["summary"], w)
    cands = candidates(ctx, base, cfg, cur)
    overlay: dict = {}
    obj_cur = obj0

    def gain(c: dict) -> float:
        return obj_cur - objective(run_flood(ctx, params, _merge(overlay, c["overlay"]))["summary"], w)

    heap = []
    for i, c in enumerate(cands):
        g = gain(c)
        if g > 0 and c["cost"] > 0:
            heapq.heappush(heap, (-g / c["cost"], i, 0, g))
    spent, plan, version = 0.0, [], 0
    curve = [{"cost": 0, "objective": obj0}]
    while heap and len(plan) < cfg["max_steps"]:
        neg, i, ver, g = heapq.heappop(heap)
        c = cands[i]
        if spent + c["cost"] > budget:
            continue  # cannot afford this one; cheaper ones may still fit
        if ver != version:  # stale gain → re-evaluate against the current plan (lazy greedy)
            g = gain(c)
            if g > 0:
                heapq.heappush(heap, (-g / c["cost"], i, version, g))
            continue
        overlay = _merge(overlay, c["overlay"])
        spent += c["cost"]
        res = run_flood(ctx, params, overlay)
        obj_cur = objective(res["summary"], w)
        version += 1
        plan.append({"step": len(plan) + 1, "kind": c["kind"], "asset_id": c["asset_id"], "label": c["label"],
                     "cost": c["cost"], "gain": round(g, 2), "risk_per_unit_cost": round(g / c["cost"] * 1e6, 3),
                     "cumulative_cost": round(spent), "objective_after": obj_cur})
        curve.append({"cost": round(spent), "objective": obj_cur})
    after = run_flood(ctx, params, overlay) if plan else base
    keys = ("drains_overloaded", "drains_total", "road_km_impassable", "buildings_exposed", "transformers_shutdown",
            "buildings_power_loss", "facilities_affected")
    return {"label": LABEL, "data_status": "modelled", "params": params, "budget": budget, "spent": round(spent),
            "objective_formula": " + ".join(f"{v} × {k.replace('_', ' ')}" for k, v in w.items()),
            "objective_before": obj0, "objective_after": objective(after["summary"], w),
            "risk_removed_pct": round(100 * (obj0 - objective(after["summary"], w)) / obj0, 1) if obj0 else 0.0,
            "before": {k: base["summary"].get(k) for k in keys}, "after": {k: after["summary"].get(k) for k in keys},
            "plan": plan, "curve": curve, "candidates_considered": len(cands),
            "unit_costs": {k: v for k, v in cur.items() if k.endswith(("_per_m", "_per_transformer", "_per_m3"))},
            "after_result": after}
