"""P10: SIMULATED electrical distribution network for the pilot (D-09) → data/processed/power.gpkg.

Substations: OSM (curated position, ratings assumed). Transformers: synthetic — buildings grouped so each
group's peak ≤ largest distribution unit / 1.25; buildings above that get dedicated HT transformer(s).
Feeders are schematic straight polylines (substation → transformers in nearest-neighbour order), not real routes.
Run after build_drainage + make_sites:  python -m pipelines.build_power
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points
from sklearn.cluster import KMeans

from pipelines.osm_common import ROOT

UTM = 32645
G = ROOT / "data" / "processed" / "hyperborea.gpkg"
OUT = ROOT / "data" / "processed" / "power.gpkg"
NORMS = yaml.safe_load((ROOT / "config" / "norms.yaml").read_text(encoding="utf-8"))
DIST_RATINGS = [100, 160, 250, 400, 630]      # kVA distribution transformers (11 kV / 433 V)
HT_RATINGS = [1000, 1600, 2000, 2500]         # dedicated HT consumer transformers
MARGIN = 1.25                                 # rating ≥ 1.25 × peak
PLINTH_M = 0.6                                # planning §7
SUBSTATION_PLINTH_M = 1.2                     # assumed raised above the 1.0 m modelled ponding cap
N_FEEDERS = 8
SEED = 42
PRIMARY = "Mahishbathan 33/11 KV Sub-Station"  # OSM substation inside the pilot
UPSTREAM = "Salt Lake"                          # OSM grid substation inside the pilot (132/33 kV assumed)
COMMERCIAL_LU = {"commercial", "industrial", "retail", "construction"}
COMMERCIAL_USE = {"office", "commercial", "retail", "industrial", "college", "university", "hospital", "hotel"}


def building_loads(b: gpd.GeoDataFrame, lu: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    a = b["attrs"].map(json.loads)
    cen = b.geometry.representative_point()
    hit = gpd.sjoin(gpd.GeoDataFrame(geometry=cen, crs=UTM), lu[["asset_type", "geometry"]], predicate="within")
    hit = hit[~hit.index.duplicated()]
    landuse = hit.asset_type.reindex(b.index)
    levels = a.map(lambda x: x.get("levels") or max(1, round(x["height_m"] / NORMS["floor_height_m"])))
    area = a.map(lambda x: x["area_m2"])
    use_tag = a.map(lambda x: x.get("amenity") or x.get("use"))
    cls, why = [], []
    for u, l, ar in zip(use_tag, landuse, area):
        if u in COMMERCIAL_USE:
            cls.append("commercial"); why.append(f"building tag '{u}'")
        elif u in {"residential", "apartments", "house"}:
            cls.append("residential"); why.append(f"building tag '{u}'")
        elif isinstance(l, str):
            cls.append("commercial" if l in COMMERCIAL_LU else "residential"); why.append(f"OSM landuse '{l}'")
        else:
            cls.append("residential" if ar < 200 else "commercial"); why.append("no tag/landuse: footprint < 200 m² → residential")
    el = NORMS["electrical"]
    w = [NORMS["uses"][c]["electrical_w_per_m2"] for c in cls]
    kva = area * levels * np.array(w) * el["diversity_factor"] / 1000 / el["power_factor"]
    return b.assign(levels=levels, bua=area * levels, load_class=cls, load_basis=why, load_kva=kva.round(1))


def split_groups(xy: np.ndarray, load: np.ndarray, cap: float) -> list[np.ndarray]:
    """k-means start, then bisect any group whose peak exceeds cap (deterministic)."""
    k = max(1, math.ceil(load.sum() / (cap * 0.7)))
    lab = KMeans(n_clusters=min(k, len(xy)), n_init=4, random_state=SEED).fit_predict(xy)
    todo = [np.where(lab == i)[0] for i in range(lab.max() + 1)]
    out = []
    while todo:
        idx = todo.pop()
        if load[idx].sum() <= cap or len(idx) == 1:
            out.append(idx)
            continue
        sub = KMeans(n_clusters=2, n_init=4, random_state=SEED).fit_predict(xy[idx])
        todo += [idx[sub == 0], idx[sub == 1]]
    return out


def rating_for(peak: float) -> tuple[int, int, str]:
    need = peak * MARGIN
    for r in DIST_RATINGS:
        if r >= need:
            return r, 1, "distribution"
    units = math.ceil(need / HT_RATINGS[-1])
    per = next(r for r in HT_RATINGS if r * units >= need)
    return per, units, "dedicated HT"


def main() -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    bnd = gpd.read_file(G, layer="boundary").to_crs(UTM).geometry.iloc[0]
    b = gpd.read_file(G, layer="buildings").to_crs(UTM)
    lu = gpd.read_file(G, layer="landuse").to_crs(UTM)
    roads = gpd.read_file(G, layer="roads").to_crs(UTM)
    roads = roads[roads.intersects(bnd.buffer(50))]
    road_union = roads.geometry.union_all()
    fac = gpd.read_file(G, layer="facilities").to_crs(UTM)
    fac = fac[fac.in_pilot.astype(bool)]
    osm = gpd.read_file(G, layer="osm_power").to_crs(UTM)
    b = building_loads(b, lu)

    # --- substations (OSM positions, curated) ---
    subs = osm[osm.asset_type == "substation"]
    prim = subs[subs["name"] == PRIMARY]
    up = subs[subs["name"] == UPSTREAM]
    sub_rows = []
    for row, role, kv, mva in ((prim, "primary 33/11 kV (assumed 2 × 31.5 MVA)", "33/11", 63), (up, "grid 132/33 kV (assumed)", "132/33", 150)):
        if row.empty:
            continue
        r = row.iloc[0]
        sub_rows.append({"asset_id": f"sub_cur_{r.asset_id.split('_')[-1]}", "name": r["name"], "role": role,
                         "kv": kv, "rating_mva": mva, "osm_id": r.asset_id, "geometry": r.geometry.representative_point()})
    if not sub_rows:  # fallback: synthetic central substation
        sub_rows.append({"asset_id": "sub_syn_central", "name": "Synthetic 33/11 kV substation", "role": "primary 33/11 kV",
                         "kv": "33/11", "rating_mva": 40, "osm_id": None, "geometry": bnd.representative_point()})
    primary = sub_rows[0]

    # --- transformers ---
    big = DIST_RATINGS[-1] / MARGIN
    xy = np.c_[b.geometry.representative_point().x, b.geometry.representative_point().y]
    load = b.load_kva.to_numpy()
    small = np.where(load <= big)[0]
    groups = [small[g] for g in split_groups(xy[small], load[small], big)] + [np.array([i]) for i in np.where(load > big)[0]]
    trf = []
    for k, idx in enumerate(sorted(groups, key=lambda g: (xy[g, 0].mean(), xy[g, 1].mean())), 1):
        peak = float(load[idx].sum())
        rating, units, kind = rating_for(peak)
        centre = Point(xy[idx, 0].mean(), xy[idx, 1].mean())
        site = nearest_points(road_union, centre)[0]  # pole/plinth on the road edge nearest the group centre
        trf.append({"asset_id": f"trf_syn_{k:03d}", "kind": kind, "units": units, "rating_kva": rating * units,
                    "unit_kva": rating, "load_kva": round(peak, 1), "loading_pct": round(100 * peak / (rating * units), 1),
                    "buildings": list(b.asset_id.iloc[idx]), "geometry": site})
    t = gpd.GeoDataFrame(trf, crs=UTM)
    # facilities → nearest transformer
    nf = gpd.sjoin_nearest(fac[["asset_id", "geometry"]].rename(columns={"asset_id": "fid"}), t[["asset_id", "geometry"]])
    fac_of = nf.groupby("asset_id").fid.apply(list).to_dict()
    t["facilities"] = t.asset_id.map(lambda a: fac_of.get(a, []))

    # --- feeders: radial sectors around the primary substation, nearest-neighbour chains ---
    sp = primary["geometry"]
    ang = np.arctan2(t.geometry.y - sp.y, t.geometry.x - sp.x)
    t["feeder"] = ((ang + math.pi) / (2 * math.pi) * N_FEEDERS).astype(int).clip(0, N_FEEDERS - 1) + 1
    feeders = []
    for f, grp in t.groupby("feeder"):
        left, chain, cur = list(grp.index), [], sp
        while left:
            j = min(left, key=lambda i: cur.distance(t.geometry.loc[i]))
            chain.append(j)
            left.remove(j)
            cur = t.geometry.loc[j]
        feeders.append({"asset_id": f"fdr_syn_{f:02d}", "name": f"11 kV feeder F{f} (schematic)",
                        "transformers": list(t.asset_id.loc[chain]), "load_kva": round(t.load_kva.loc[chain].sum(), 1),
                        "geometry": LineString([sp] + [t.geometry.loc[i] for i in chain])})
    t["feeder_id"] = t.feeder.map(lambda f: f"fdr_syn_{f:02d}")
    t["substation_id"] = primary["asset_id"]

    # --- write ---
    def frame(rows, geoms, atype, status, src, assumptions, conf, names=None):
        return gpd.GeoDataFrame({
            "asset_id": [r["asset_id"] for r in rows], "asset_type": atype,
            "name": names or [r.get("name") for r in rows], "data_status": status, "source_id": src,
            "observed_at": None, "ingested_at": now, "confidence": conf, "assumptions": assumptions,
            "attrs": [json.dumps({k: v for k, v in r.items() if k not in ("asset_id", "geometry", "name")}, default=str)
                      for r in rows],
            "in_pilot": [g.within(bnd.buffer(1)) for g in geoms],
        }, geometry=list(geoms), crs=UTM).to_crs(4326)

    sub_rows[0]["supplies_from"] = sub_rows[1]["asset_id"] if len(sub_rows) > 1 else None
    for s in sub_rows:
        s["plinth_m"] = SUBSTATION_PLINTH_M
    subs_g = frame(sub_rows, [s["geometry"] for s in sub_rows], "substation", "curated", "osm",
                   f"Position from OSM; rating assumed; plinth {SUBSTATION_PLINTH_M} m assumed (raised above modelled ponding)", "med")
    t_rows = []
    for r in t.to_dict("records"):
        r = {**r, "plinth_m": PLINTH_M, "n_buildings": len(r["buildings"]), "n_facilities": len(r["facilities"])}
        r.pop("feeder")
        t_rows.append(r)
    t_g = frame(t_rows, t.geometry, "transformer", "simulated", "syn_power",
                f"SIMULATED: buildings grouped to peak ≤ {big:.0f} kVA (k-means + bisection, seed {SEED}); rating = smallest "
                f"standard ≥ {MARGIN}× peak ({DIST_RATINGS} kVA; dedicated HT {HT_RATINGS} kVA); on nearest road; "
                f"plinth {PLINTH_M} m; load = BUA × W/m² × diversity {NORMS['electrical']['diversity_factor']} / pf "
                f"{NORMS['electrical']['power_factor']}", "low",
                names=[f"{r['kind']} transformer {r['asset_id'][-3:]} ({r['rating_kva']} kVA)" for r in t_rows])
    f_g = frame(feeders, [f["geometry"] for f in feeders], "feeder", "simulated", "syn_power",
                "SCHEMATIC straight-line 11 kV feeder (radial sector, nearest-neighbour order) — not a real cable route", "low")
    OUT.unlink(missing_ok=True)
    for name, gdf in (("substations", subs_g), ("transformers", t_g), ("feeders", f_g)):
        gdf.to_file(OUT, layer=name, driver="GPKG", layer_options={"SPATIAL_INDEX": "NO"})
    print(f"buildings {len(b)} · total peak {b.load_kva.sum() / 1000:.1f} MVA "
          f"({(b.load_class == 'commercial').mean():.0%} commercial density) · max building {b.load_kva.max():.0f} kVA")
    print(f"transformers {len(t)} ({(t.kind == 'distribution').sum()} distribution, {(t.kind != 'distribution').sum()} dedicated HT) · "
          f"loading % median {t.loading_pct.median():.0f} max {t.loading_pct.max():.0f} · feeders {len(feeders)} · "
          f"substations {[s['name'] for s in sub_rows]}")
    print("ratings:", t.unit_kva.value_counts().sort_index().to_dict(), "· facilities supplied", int(t.facilities.map(len).sum()))


if __name__ == "__main__":
    main()
