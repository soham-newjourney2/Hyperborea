"""P09 development assessment on a scenario overlay (planning §7 norms + verdict, VISION §10).

assess(): proposed footprint + use + floors + upgrades + design preset → derived demands, seven checks
(pass | conditional | fail | insufficient_data, each with numbers), the §7 verdict wording and a transparent
weighted index. Never mutates baseline layers or the graph; never says "approved".
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache

import geopandas as gpd
import yaml
from shapely.geometry import Polygon, shape

from ..app.core.paths import CONFIG
from .flood import FloodContext, run_flood
from .hydraulics import manning_full_circular, next_pipe_size, rational_runoff
from ..app.core.regions import metric_crs as utm  # P16: active region's UTM zone (Sector V = 32645)

LABEL = "Screening assessment — not an approval"
DATA_STATUS = "modelled (simulated drainage, assumed norms)"
VERDICTS = {
    "fail": "Potentially unsuitable under current assumptions",
    "conditional": "Conditionally suitable — upgrades or further assessment required",
    "insufficient": "Insufficient data",
    "pass": "Suitable under current assumptions",
}
SCORE = {"pass": 1.0, "conditional": 0.5, "fail": 0.0}
UPGRADES = {
    "detention": "On-site detention / rainwater-harvesting tank sized for no net increase in peak runoff (≥ 40 % cut)",
    "drain_upsize": "Upsize the receiving drain one standard pipe size",
    "transformer": "New / up-rated transformer (takes effect with P10 electrical data)",
}


@lru_cache
def norms() -> dict:
    return yaml.safe_load((CONFIG / "norms.yaml").read_text(encoding="utf-8"))


def _attrs(s):
    return json.loads(s) if isinstance(s, str) else (s or {})


def _road_class(h) -> str:
    h = str(h or "")
    if any(k in h for k in ("trunk", "primary")):
        return "arterial"
    if any(k in h for k in ("secondary", "tertiary")):
        return "secondary"
    return "local"


def verdict(statuses: dict[str, str], key: list[str]) -> str:
    """planning §7: any fail → unsuitable; any conditional → conditional; ≥ 2 key insufficient → insufficient."""
    vals = set(statuses.values())
    if "fail" in vals:
        return VERDICTS["fail"]
    if "conditional" in vals:
        return VERDICTS["conditional"]
    if sum(statuses.get(k) == "insufficient_data" for k in key) >= 2:
        return VERDICTS["insufficient"]
    return VERDICTS["pass"]


def suitability_index(statuses: dict[str, str], weights: dict[str, float]) -> dict:
    used = {k: w for k, w in weights.items() if statuses.get(k) in SCORE}
    tot = sum(used.values())
    val = sum(w * SCORE[statuses[k]] for k, w in used.items()) / tot if tot else None
    return {"value": None if val is None else round(val, 3), "weights": weights,
            "scores": {k: SCORE.get(statuses.get(k)) for k in weights},
            "label": "screening index (0–1) over assessed dimensions — not an approval"}


def _downstream(ctx: FloodContext, d: str) -> list[str]:
    path, cur, seen = [d], d, {d}
    while (nxt := ctx.drain[cur]["drains_to"]) in ctx.drain and nxt not in seen:
        path.append(nxt)
        seen.add(nxt)
        cur = nxt
    return path


def assess(ctx: FloodContext, layers: dict[str, gpd.GeoDataFrame], presets: list[dict], params: dict,
           access=None) -> dict:
    nm = norms()
    ck = nm["checks"]
    use, floors = params["use"], int(params["floors"])
    upgrades = sorted(set(params.get("upgrades") or []))
    if use not in nm["uses"]:
        raise ValueError(f"use must be one of {sorted(nm['uses'])}")
    if not 1 <= floors <= 60:
        raise ValueError("floors must be 1–60")
    bad = set(upgrades) - set(UPGRADES)
    if bad:
        raise ValueError(f"unknown upgrades {sorted(bad)}")

    # ---- geometry ----------------------------------------------------------------------------------
    site_attrs, site_id = {}, params.get("site_id")
    if site_id:
        s = layers["sites"]
        row = s[(s.asset_id == site_id) | (s["attrs"].map(lambda a: _attrs(a).get("site_id")) == site_id)]
        if row.empty:
            raise KeyError(site_id)
        geom4326, site_attrs, site_id = row.geometry.iloc[0], _attrs(row["attrs"].iloc[0]), row.asset_id.iloc[0]
    else:
        geom4326 = shape(params["geometry"])
        if not isinstance(geom4326, Polygon) or not geom4326.is_valid:
            raise ValueError("geometry must be a valid GeoJSON Polygon")
    g = gpd.GeoSeries([geom4326], crs=4326).to_crs(utm())
    poly, centre = g.iloc[0], g.centroid.iloc[0]
    boundary = layers["boundary"].to_crs(utm()).geometry.iloc[0]
    if not poly.within(boundary.buffer(1)):
        raise ValueError("proposed footprint must lie inside the pilot boundary")
    area = poly.area
    if not 100 <= area <= 50_000:
        raise ValueError(f"footprint {area:.0f} m² outside the screening range 100–50 000 m²")

    # ---- derived demands ---------------------------------------------------------------------------
    u = nm["uses"][use]
    bua = area * floors
    occupants = bua / u["occupancy_m2_per_person"]
    water_kld = occupants * u["water_lpcd"] / 1000
    kva = bua * u["electrical_w_per_m2"] * nm["electrical"]["diversity_factor"] / 1000 / nm["electrical"]["power_factor"]
    pre = next((p for p in presets if p["id"] == params.get("design_preset", "design")), None)
    if pre is None:
        raise KeyError(params.get("design_preset"))
    rain, dur = pre["rain_mm_h"], pre["duration_h"]
    c0, c1 = nm["runoff"]["site_c_before"], nm["runoff"]["site_c_after"]
    q_before = rational_runoff(c0, rain, area)
    q_raw = rational_runoff(c1, rain, area)
    det, tank_m3 = 0.0, 0.0
    if "detention" in upgrades:  # min cut, or enough for no net increase over pre-development peak
        up = nm["upgrades"]
        det = max(up["detention_peak_reduction"], 1 - c0 / c1 if up.get("detention_no_net_increase") else 0.0)
        tank_m3 = q_raw * det * dur * 3600
    q_after = q_raw * (1 - det)
    dq = q_after - q_before
    derived = {
        "footprint_m2": round(area, 1), "floors": floors, "height_m": round(floors * nm["floor_height_m"], 1),
        "built_up_area_m2": round(bua, 0), "occupants": round(occupants), "water_kl_day": round(water_kld, 1),
        "electrical_kva": round(kva, 0), "site_runoff_before_m3s": round(q_before, 4),
        "site_runoff_after_m3s": round(q_after, 4), "added_runoff_m3s": round(dq, 4),
        "detention_peak_cut": round(det, 3), "detention_tank_m3": round(tank_m3, 0),
        "design_rain_mm_h": rain, "design_duration_h": dur,
    }

    # ---- context: catchment, receiving drain, land use, road, facilities ---------------------------
    cats = layers["catchments"].to_crs(utm())
    hit = cats[cats.contains(centre)]
    cat_id = hit.asset_id.iloc[0] if len(hit) else None
    recv = ctx.cat[cat_id]["drain_id"] if cat_id in ctx.cat else None
    lu = layers["landuse"].to_crs(utm())
    lu_hit = lu[lu.contains(centre)]
    landuse = lu_hit.asset_type.iloc[0] if len(lu_hit) else None
    roads = layers["roads"].to_crs(utm())
    dist = roads.distance(poly)
    ri = dist.idxmin()
    road_id, road_d = roads.asset_id.loc[ri], float(dist.loc[ri])
    road_cls = _road_class(_attrs(roads["attrs"].loc[ri]).get("highway"))
    fac = layers["facilities"].to_crs(utm())
    near = {}
    for t in ("hospital", "fire_station"):
        f = fac[fac.asset_type == t]
        if len(f):
            dd = f.distance(centre)
            j = dd.idxmin()
            nm_ = f["name"].loc[j]
            near[t] = {"asset_id": f.asset_id.loc[j], "name": nm_ if isinstance(nm_, str) else None,
                       "distance_m": round(float(dd.loc[j]))}

    # ---- flood runs: baseline vs proposal overlay (scenario only) ----------------------------------
    fp = {"preset": pre["id"], "preset_source_id": pre["source_id"], "rain_mm_h": rain, "duration_h": dur,
          "condition_scale": 1.0}
    base = run_flood(ctx, fp)
    overlay = {"extra_inflow": {recv: dq} if recv else {}, "capacity": {}}
    upsized = None
    if recv and "drain_upsize" in upgrades:
        v = ctx.drain[recv]
        d_new = next_pipe_size(v["diameter_m"], nm["upgrades"]["drain_upsize_steps"])
        overlay["capacity"][recv] = manning_full_circular(d_new, v["slope"], v["manning_n"])
        upsized = {"drain_id": recv, "diameter_from_m": v["diameter_m"], "diameter_to_m": d_new}
    prop = run_flood(ctx, fp, overlay)

    checks: dict[str, dict] = {}
    # Drainage — judged on what the proposal itself does (receiving drain + downstream path to the outfall)
    if recv:
        path = _downstream(ctx, recv)
        rb = {d: base["layers"]["drains"][d]["load_ratio"] for d in path}
        ra = {d: prop["layers"]["drains"][d]["load_ratio"] for d in path}
        down = path[1:]
        worst = max(down, key=lambda d: ra[d]) if down else None
        lim = ck["drainage"]
        full = lim["conditional_max_ratio"]
        tipped = [d for d in path if rb[d] <= full < ra[d]]
        preexisting = [d for d in path if rb[d] > full]
        reasons = []
        if tipped:
            st = "fail"
            reasons.append(f"proposal pushes {len(tipped)} drain(s) over capacity (e.g. {tipped[0]}: "
                           f"{rb[tipped[0]]:.2f} → {ra[tipped[0]]:.2f}×)")
        else:
            if ra[recv] > lim["pass_max_ratio"]:
                reasons.append(f"receiving drain at {ra[recv]:.0%} of capacity (> {lim['pass_max_ratio']:.0%} headroom limit)")
            if preexisting and dq > 1e-6:
                reasons.append(f"{len(preexisting)} drain(s) on the path already overloaded under '{pre['id']}' "
                               f"(worst {max(rb[d] for d in preexisting):.2f}×) — proposal still adds {dq * 1000:.1f} L/s")
            st = "conditional" if reasons else "pass"
            if not reasons:
                reasons.append(f"receiving drain at {ra[recv]:.0%}, downstream path within capacity")
        checks["drainage"] = {"status": st, "value": round(ra[recv], 3), "unit": "receiving-drain load ratio",
                              "detail": "; ".join(reasons),
                              "numbers": {"receiving_drain": recv, "load_before": rb[recv], "load_after": ra[recv],
                                          "worst_downstream": worst, "worst_downstream_after": ra[worst] if worst else None,
                                          "added_runoff_m3s": round(dq, 4), "path_drains": len(path),
                                          "preexisting_overloads": len(preexisting), "upsized": upsized},
                              "threshold": f"fail if the proposal tips any drain over capacity; conditional if receiving "
                                           f"drain > {lim['pass_max_ratio']:.0%} or the path is already overloaded",
                              "data_status": "simulated", "source_ids": ["syn_drain", "syn_rain"]}
    else:
        checks["drainage"] = {"status": "insufficient_data", "detail": "site not inside a modelled catchment",
                              "data_status": "unknown", "source_ids": []}
    # Flood exposure
    depth = prop["layers"]["catchments"].get(cat_id, {}).get("depth_m", 0.0) if cat_id else None
    if depth is None:
        checks["flood_exposure"] = {"status": "insufficient_data", "detail": "no catchment", "data_status": "unknown", "source_ids": []}
    else:
        fl = ck["flood"]
        st = "fail" if depth >= fl["fail_from_m"] else "conditional" if depth >= fl["conditional_from_m"] else "pass"
        checks["flood_exposure"] = {"status": st, "value": depth, "unit": "m ponding",
                                    "detail": f"{depth:.2f} m ponding at the site under '{pre['id']}' "
                                              f"({rain} mm/h × {dur} h)" + (" — raise plinth / flood-proof ground floor"
                                                                            if st != "pass" else ""),
                                    "threshold": f"conditional ≥ {fl['conditional_from_m']} m, fail ≥ plinth {fl['fail_from_m']} m",
                                    "numbers": {"catchment_id": cat_id}, "data_status": "modelled",
                                    "source_ids": ["syn_drain", "syn_rain", "cop_dem"]}
    # Road access
    if road_d > ck["road_access"]["max_distance_m"]:
        checks["road_access"] = {"status": "fail", "value": round(road_d), "unit": "m",
                                 "detail": f"no road within {ck['road_access']['max_distance_m']} m",
                                 "data_status": "observed", "source_ids": ["osm"]}
    else:
        flooded = prop["layers"]["roads"].get(road_id, {}).get("state")
        busy = use == "commercial" and occupants > 500 and road_cls == "local"
        st = "conditional" if (flooded == "impassable" or busy) else "pass"
        detail = f"{road_cls} road at {road_d:.0f} m"
        if busy:
            detail += f"; {occupants:,.0f} occupants on a local road — traffic assessment needed"
        if flooded == "impassable":
            detail += f"; access road impassable under '{pre['id']}'"
        checks["road_access"] = {"status": st, "value": round(road_d), "unit": "m", "detail": detail,
                                 "numbers": {"road_id": road_id, "class": road_cls, "flood_state": flooded},
                                 "threshold": f"≤ {ck['road_access']['max_distance_m']} m; local road + > 500 commercial occupants → conditional",
                                 "data_status": "observed", "source_ids": ["osm"]}
    # Critical facilities: free-flow drive time (P12) — straight-line fallback without the drive graph
    lim = ck["facilities"]
    if access is not None:
        from .access import minutes_from, nearest_node
        c4326 = gpd.GeoSeries([centre], crs=utm()).to_crs(4326).iloc[0]
        node = nearest_node(access, c4326.x, c4326.y)
        tmin = {t: minutes_from(access, access.baseline, cat, node) for t, cat in (("hospital", "hospital"), ("fire_station", "fire"))}
        if any(v is None for v in tmin.values()):
            checks["critical_facilities"] = {"status": "fail", "detail": "no drive route to a hospital or fire station",
                                             "data_status": "modelled", "source_ids": ["osm"]}
        else:
            worst = max(tmin.values())
            st = "pass" if worst <= lim["pass_within_min"] else "conditional" if worst <= lim["conditional_within_min"] else "fail"
            to = {t: access.baseline[cat]["nodes"][node][1] for t, cat in (("hospital", "hospital"), ("fire_station", "fire"))}
            names = {t: (access.facilities[f]["name"] or "(unnamed)") for t, f in to.items()}
            checks["critical_facilities"] = {
                "status": st, "value": round(worst, 1), "unit": "min drive (free-flow)",
                "detail": f"hospital {names['hospital']} {tmin['hospital']:.1f} min; fire station {names['fire_station']} "
                          f"{tmin['fire_station']:.1f} min",
                "numbers": {"minutes": tmin, "to": to, "node": node, "straight_line_m": {k: v["distance_m"] for k, v in near.items()}},
                "threshold": f"pass ≤ {lim['pass_within_min']} min, conditional ≤ {lim['conditional_within_min']} min",
                "data_status": "modelled", "source_ids": ["osm"], "note": "free-flow travel time — not live traffic"}
    elif len(near) < 2:
        checks["critical_facilities"] = {"status": "insufficient_data", "detail": "hospital or fire station not mapped nearby",
                                         "data_status": "unknown", "source_ids": ["osm"]}
    else:
        far = max(v["distance_m"] for v in near.values())
        st = "pass" if far <= lim["pass_within_m"] else "conditional" if far <= lim["conditional_within_m"] else "fail"
        checks["critical_facilities"] = {"status": st, "value": far, "unit": "m (straight line)",
                                         "detail": "; ".join(f"{t.replace('_', ' ')} {v['name'] or '(unnamed)'} {v['distance_m']:,} m"
                                                            for t, v in near.items()),
                                         "numbers": near, "threshold": f"pass ≤ {lim['pass_within_m']} m, conditional ≤ {lim['conditional_within_m']} m",
                                         "data_status": "observed", "source_ids": ["osm"],
                                         "note": "straight-line distance (drive graph not loaded)"}
    # Electrical (P10, simulated network): nearest transformer headroom after the added kVA
    tl = layers.get("transformers")
    if tl is None or tl.empty:
        checks["electrical"] = {"status": "insufficient_data", "value": round(kva), "unit": "kVA demand",
                                "detail": f"needs ~{kva:,.0f} kVA; no distribution network loaded",
                                "data_status": "unknown", "source_ids": ["norms"]}
    else:
        tu = tl.to_crs(utm())
        dd = tu.distance(centre)
        j = dd.idxmin()
        tid, ta = tu.asset_id.loc[j], _attrs(tu["attrs"].loc[j])
        rating, load = float(ta["rating_kva"]), float(ta["load_kva"])
        el, lim = nm["electrical"], ck["electrical"]
        shut = tid in prop["layers"].get("transformers", {})
        if "transformer" in upgrades:
            need = kva * el["transformer_margin"]
            units = 1
            while not any(r * units >= need for r in el["transformer_kva"]):
                units += 1
            unit = next(r for r in el["transformer_kva"] if r * units >= need)
            new_r = unit * units
            ratio = kva / new_r
            detail = (f"new dedicated {units} × {unit} kVA transformer for the site ({kva:,.0f} kVA → {ratio:.0%}); "
                      f"existing {tid} stays at {load / rating:.0%}")
            nums = {"transformer": tid, "existing_rating_kva": rating, "existing_load_kva": load, "new_rating_kva": new_r}
        else:
            ratio = (load + kva) / rating
            detail = (f"nearest transformer {tid} ({rating:.0f} kVA, {dd.loc[j]:.0f} m): {load:,.0f} + {kva:,.0f} kVA "
                      f"= {ratio:.0%} of rating")
            nums = {"transformer": tid, "rating_kva": rating, "load_before_kva": load, "added_kva": round(kva),
                    "distance_m": round(float(dd.loc[j]))}
        st = "pass" if ratio <= lim["pass_max_loading"] else "conditional" if ratio <= lim["conditional_max_loading"] else "fail"
        if shut and st == "pass":
            st = "conditional"
        if shut:
            detail += f"; this transformer shuts down (flooded) under '{pre['id']}'"
        checks["electrical"] = {"status": st, "value": round(ratio, 3), "unit": "transformer loading",
                                "detail": detail, "numbers": nums,
                                "threshold": f"pass ≤ {lim['pass_max_loading']:.0%}, conditional ≤ {lim['conditional_max_loading']:.0%}",
                                "data_status": "simulated", "source_ids": ["syn_power", "norms"],
                                "note": "simulated distribution network — not the utility's grid"}
    checks["water_supply"] = {"status": "insufficient_data", "value": round(water_kld, 1), "unit": "kL/day demand",
                              "detail": f"needs ~{water_kld:,.0f} kL/day; no public water-supply network data for the pilot",
                              "data_status": "unknown", "source_ids": ["norms"]}
    # Land use
    ok = nm["checks"]["landuse_compatible"][use]
    if landuse is None:
        checks["land_use"] = {"status": "insufficient_data", "detail": "no OSM land-use polygon at the site",
                              "data_status": "unknown", "source_ids": ["osm"]}
    else:
        st = "pass" if landuse in ok else "conditional"
        checks["land_use"] = {"status": st, "value": landuse, "unit": "OSM landuse",
                              "detail": f"OSM landuse '{landuse}' {'compatible with' if st == 'pass' else 'differs from'} {use}"
                                        + ("" if st == "pass" else " — change-of-use permission needed"),
                              "threshold": f"{use}: {', '.join(ok)}", "data_status": "observed", "source_ids": ["osm"]}

    order = ["drainage", "flood_exposure", "road_access", "critical_facilities", "electrical", "water_supply", "land_use"]
    statuses = {k: checks[k]["status"] for k in order}
    v = verdict(statuses, nm["key_dimensions"])
    pid = "prop_" + hashlib.sha1(json.dumps({**params, "upgrades": upgrades}, sort_keys=True).encode()).hexdigest()[:10]
    overlay_graph = {
        "node": {"id": pid, "kind": "proposed_site", "data_status": "simulated", "use": use, "floors": floors},
        "edges": [e for e in (
            {"type": "LOCATED_WITHIN", "source": pid, "target": cat_id, "rule": "footprint centroid inside catchment"} if cat_id else None,
            {"type": "PROPOSED_ADJACENT_TO", "source": pid, "target": recv, "rule": "site runoff enters this drain"} if recv else None,
            {"type": "ACCESSIBLE_VIA", "source": pid, "target": road_id, "rule": f"nearest road ({road_d:.0f} m)"}
            if road_d <= ck["road_access"]["max_distance_m"] else None) if e],
        "note": "scenario-only overlay — the baseline graph is not modified",
    }
    return {
        "assessment_id": pid, "label": LABEL, "data_status": DATA_STATUS,
        "params": {**{k: params.get(k) for k in ("site_id", "use", "floors", "design_preset")}, "site_id": site_id,
                   "upgrades": upgrades},
        "upgrades_applied": [{"id": x, "label": UPGRADES[x]} for x in upgrades],
        "geometry": json.loads(gpd.GeoSeries([geom4326], crs=4326).to_json())["features"][0]["geometry"],
        "site": site_attrs, "derived": derived,
        "checks": [{"dimension": k, **checks[k]} for k in order],
        "verdict": v, "index": suitability_index(statuses, nm["weights"]),
        "key_dimensions": nm["key_dimensions"], "overlay": overlay_graph,
        "assumptions": [
            "Screening-level norms (config/norms.yaml); no statutory FAR / bye-law checks.",
            f"Site runoff C {c0} → {c1}; detention tank sized for no net increase in peak runoff "
            f"(≥ {nm['upgrades']['detention_peak_reduction']:.0%} cut, assumed).",
            "Drainage + flood use the simulated P06 network and the P08 engine under the chosen design preset.",
            "Critical-facility check uses free-flow drive time on the OSM network (P12), not live traffic.",
            "Electrical headroom uses the SIMULATED P10 network (nearest transformer); real feeder data would replace it.",
        ],
    }


def what_changed(a: dict, b: dict) -> list[str]:
    """Human-readable differences between two assessments (for the A/B/C compare view)."""
    notes = []
    if a["params"].get("site_id") != b["params"].get("site_id"):
        notes.append(f"site {a['params'].get('site_id') or 'drawn'} → {b['params'].get('site_id') or 'drawn'}")
    if a["params"]["upgrades"] != b["params"]["upgrades"]:
        notes.append(f"upgrades {', '.join(a['params']['upgrades']) or 'none'} → {', '.join(b['params']['upgrades']) or 'none'}")
    ca = {c["dimension"]: c for c in a["checks"]}
    for c in b["checks"]:
        o = ca[c["dimension"]]
        if o["status"] != c["status"] or o.get("value") != c.get("value"):
            val = f" ({o.get('value')} → {c.get('value')} {c.get('unit', '')})" if o.get("value") != c.get("value") else ""
            notes.append(f"{c['dimension'].replace('_', ' ')}: {o['status']} → {c['status']}{val}")
    if a["verdict"] != b["verdict"]:
        notes.append(f"verdict: {a['verdict']} → {b['verdict']}")
    return notes
