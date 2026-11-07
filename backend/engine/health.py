"""P14 infrastructure health: condition index 0–100 (100 = healthy) for drains, transformers and roads.

index = 100 · (1 − Σ wᵢ · stressᵢ), stress components in 0–1:
  age (SIMULATED) · inspection gap (SIMULATED) · utilisation under the `heavy` preset · failure frequency across
  all presets · exposure (what depends on the asset). Drains add siltation (SIMULATED condition factor).
Weights and the simulated flag of each input are returned with every result.
"""
from __future__ import annotations

import hashlib

from .flood import FloodContext, run_flood

WEIGHTS = {"age": 0.15, "inspection": 0.10, "utilisation": 0.25, "failure_frequency": 0.25, "exposure": 0.15,
           "siltation": 0.10}
SIMULATED = {"age": True, "inspection": True, "siltation": True, "utilisation": False, "failure_frequency": False,
             "exposure": False}
MAX_AGE = {"drain": 40, "transformer": 30, "road": 25}  # years (simulated range 0…max)
LABELS = {"age": "age", "inspection": "time since inspection", "utilisation": "load under heavy rain",
          "failure_frequency": "fails across presets", "exposure": "assets depending on it", "siltation": "siltation"}


def _sim(asset_id: str, salt: str) -> float:
    """Deterministic pseudo-random 0–1 per asset (SIMULATED attribute, no real records)."""
    return int(hashlib.sha1(f"{salt}:{asset_id}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def compute(ctx: FloodContext, presets: list[dict], access=None) -> dict[str, list[dict]]:
    runs = {p["id"]: run_flood(ctx, {"preset": p["id"], "preset_source_id": p["source_id"], "rain_mm_h": p["rain_mm_h"],
                                     "duration_h": p["duration_h"], "condition_scale": 1.0}) for p in presets}
    heavy = runs.get("heavy") or next(iter(runs.values()))
    n = len(runs)
    out: dict[str, list[dict]] = {"drain": [], "transformer": [], "road": []}

    def row(kind, aid, name, stress, numbers):
        w = {k: WEIGHTS[k] for k in stress}
        tot = sum(w.values())
        score = 100 * (1 - sum(w[k] * stress[k] for k in stress) / tot)
        top = sorted(stress, key=lambda k: -w[k] * stress[k])[:2]
        out[kind].append({
            "asset_id": aid, "kind": kind, "name": name, "health_index": round(score, 1),
            "components": {k: round(v, 3) for k, v in stress.items()}, "weights": w,
            "simulated_inputs": [k for k in stress if SIMULATED[k]],
            "reasons": [f"{LABELS[k]} ({stress[k]:.0%} stress{', simulated' if SIMULATED[k] else ''})" for k in top],
            "numbers": numbers})

    for d, v in ctx.drain.items():
        lr = heavy["layers"]["drains"][d]["load_ratio"]
        fails = sum(r["layers"]["drains"][d]["state"] == "overloaded" for r in runs.values())
        age = round(_sim(d, "age") * MAX_AGE["drain"])
        months = round(_sim(d, "insp") * 60)
        row("drain", d, None, {
            "age": age / MAX_AGE["drain"], "inspection": months / 60, "utilisation": min(lr / 2, 1),
            "failure_frequency": fails / n, "exposure": min((v.get("upstream_area_m2") or 0) / 5e5, 1),
            "siltation": (1 - v["condition_factor"]) / 0.4},
            {"age_years": age, "months_since_inspection": months, "heavy_load_ratio": lr, "presets_overloaded": f"{fails}/{n}",
             "upstream_area_m2": v.get("upstream_area_m2"), "condition_factor": v["condition_factor"]})
    for t, v in ctx.trf.items():
        loading = (v.get("load_kva") or 0) / max(v.get("rating_kva") or 1, 1)
        fails = sum(t in r["layers"].get("transformers", {}) for r in runs.values())
        age = round(_sim(t, "age") * MAX_AGE["transformer"])
        months = round(_sim(t, "insp") * 60)
        row("transformer", t, v.get("name"), {
            "age": age / MAX_AGE["transformer"], "inspection": months / 60, "utilisation": min(loading, 1),
            "failure_frequency": fails / n, "exposure": min(len(v["buildings"]) / 40 + 0.3 * bool(v["facilities"]), 1)},
            {"age_years": age, "months_since_inspection": months, "loading_pct": round(100 * loading, 1),
             "presets_shutdown": f"{fails}/{n}", "buildings": len(v["buildings"]), "facilities": len(v["facilities"])})
    blds_on = {}
    if access is not None:
        ends = {}
        for rid, es in access.road_edges.items():
            ends[rid] = {x for e in es for x in e}
        node_count = {}
        for nd in access.building_nodes.values():
            node_count[nd] = node_count.get(nd, 0) + 1
        blds_on = {rid: sum(node_count.get(x, 0) for x in ns) for rid, ns in ends.items()}
    for rid, v in ctx.road.items():
        depth = heavy["layers"]["roads"].get(rid, {}).get("depth_m", 0.0)
        fails = sum(rid in r["layers"]["roads"] for r in runs.values())
        age = round(_sim(rid, "age") * MAX_AGE["road"])
        months = round(_sim(rid, "insp") * 60)
        row("road", rid, v.get("name"), {
            "age": age / MAX_AGE["road"], "inspection": months / 60, "utilisation": min(depth / 0.3, 1),
            "failure_frequency": fails / n, "exposure": min(blds_on.get(rid, 0) / 20, 1)},
            {"age_years": age, "months_since_inspection": months, "heavy_water_depth_m": depth,
             "presets_impaired_or_impassable": f"{fails}/{n}", "buildings_on_road_nodes": blds_on.get(rid, 0)})
    for k in out:
        out[k].sort(key=lambda r: (r["health_index"], r["asset_id"]))
    return out
