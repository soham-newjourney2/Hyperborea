"""P02 steps 4–5: raw OSM → data/processed/hyperborea.gpkg with provenance on every feature.

Layers: boundary, buildings, roads, facilities, waterways, landuse, osm_power.
Run:  python -m pipelines.normalize_osm [raw_dir]   (default: newest data/raw/osm/*)
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import osmnx as ox
import pandas as pd
from shapely import make_valid
from shapely.geometry.base import BaseGeometry

from pipelines.osm_common import ROOT

UTM = 32645
FLOOR_M = 3.2
DEFAULT_HEIGHT_M = 9.0
GPKG = ROOT / "data" / "processed" / "hyperborea.gpkg"
PREFIX = {"node": "n", "way": "w", "relation": "r"}
POLY = ("Polygon", "MultiPolygon")
NUM = re.compile(r"\d+(?:\.\d+)?")
PILOT_ONLY = {"buildings"}  # D-18
NO_INDEX = {"SPATIAL_INDEX": "NO"}  # API loads layers into memory; rtree only costs MBs
CORE = ["asset_id", "asset_type", "name", "data_status", "source_id", "observed_at", "ingested_at",
        "confidence", "assumptions", "attrs", "in_pilot"]


def num(v) -> float | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    m = NUM.search(str(v).replace(",", "."))
    return float(m.group()) if m else None


def clean(v):
    return None if v is None or (isinstance(v, float) and pd.isna(v)) else v


def osm_ref(row) -> str:
    return f"{PREFIX[row['element']]}{row['id']}"


def fix_geom(g: BaseGeometry, polygonal: bool) -> BaseGeometry | None:
    if g is None or g.is_empty:
        return None
    if not g.is_valid:
        g = make_valid(g)
    if polygonal and g.geom_type == "GeometryCollection":
        parts = [p for p in g.geoms if p.geom_type in POLY]
        g = gpd.GeoSeries(parts).union_all() if parts else None
    return None if g is None or g.is_empty else g


def finish(gdf: gpd.GeoDataFrame, boundary, polygonal: bool, meta: dict, now: str) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    gdf["geometry"] = [fix_geom(g, polygonal) for g in gdf.geometry]
    gdf = gdf[gdf.geometry.notna()]
    if polygonal:
        gdf = gdf[gdf.geom_type.isin(POLY)]
    gdf = gdf.drop_duplicates("asset_id")
    gdf = gdf[~gdf.geometry.to_wkb().duplicated()]
    gdf["data_status"] = "observed"
    gdf["source_id"] = "osm"
    gdf["observed_at"] = meta.get("osm_data_at", meta["fetched_at"])
    gdf["ingested_at"] = now
    # UTM, like every other metric op (planning §6); roads on the boundary edge are sensitive to the CRS.
    utm_bnd = gpd.GeoSeries([boundary], crs=4326).to_crs(UTM).buffer(0.5).iloc[0]
    gdf["in_pilot"] = gdf.to_crs(UTM).representative_point().within(utm_bnd)
    gdf["name"] = gdf["name"].astype(object)  # all-null columns would otherwise round-trip as float NaN
    gdf["attrs"] = gdf["attrs"].map(lambda d: json.dumps({k: clean(v) for k, v in d.items()}, default=str))
    return gpd.GeoDataFrame(gdf[CORE + ["geometry"]], geometry="geometry", crs=4326).reset_index(drop=True)


def buildings(raw: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    raw = raw[raw.geom_type.isin(POLY)].copy()
    area = raw.to_crs(UTM).area
    rows = []
    for (i, r), a in zip(raw.iterrows(), area):
        h, lv = num(r.get("height")), num(r.get("building:levels"))
        if h:
            hs, conf, why = "observed", "high", "height from OSM height tag"
        elif lv:
            h, hs, conf, why = lv * FLOOR_M, "modelled", "med", f"height = building:levels × {FLOOR_M} m"
        else:
            h, hs, conf, why = DEFAULT_HEIGHT_M, "assumed", "low", f"no height/levels tag; {DEFAULT_HEIGHT_M} m default"
        rows.append({
            "asset_id": f"bld_osm_{osm_ref(r)}", "asset_type": "building", "name": clean(r.get("name")),
            "confidence": conf, "assumptions": why,
            "attrs": {"height_m": round(h, 1), "height_status": hs, "levels": lv, "use": r.get("building"),
                      "amenity": r.get("amenity"), "area_m2": round(a, 1), "osm_id": osm_ref(r)},
        })
    return gpd.GeoDataFrame(rows, geometry=list(raw.geometry), crs=4326)


def roads(graphml: Path) -> gpd.GeoDataFrame:
    g = ox.convert.to_undirected(ox.load_graphml(graphml))
    e = ox.graph_to_gdfs(g, nodes=False).reset_index()
    rows = [{
        "asset_id": f"rd_osm_{r['u']}_{r['v']}_{r['key']}", "asset_type": "road", "name": clean(r.get("name")),
        "confidence": "high", "assumptions": "drive network, simplified by osmnx; two-way edges merged",
        "attrs": {"highway": r.get("highway"), "length_m": round(float(r["length"]), 1), "oneway": r.get("oneway"),
                  "lanes": r.get("lanes"), "maxspeed": r.get("maxspeed"), "width": r.get("width"),
                  "u": int(r["u"]), "v": int(r["v"]), "key": int(r["key"]), "osmid": r.get("osmid")},
    } for _, r in e.iterrows()]
    return gpd.GeoDataFrame(rows, geometry=list(e.geometry), crs=4326)


def facility_type(r) -> str | None:
    if clean(r.get("amenity")) in {"hospital", "clinic", "school", "college", "university", "fire_station", "police"}:
        return r["amenity"]
    if clean(r.get("station")) == "subway" or "subway" in str(r.get("railway", "")) or clean(r.get("subway")) == "yes":
        return "metro_station"
    if clean(r.get("railway")) in {"station", "halt"}:
        return "rail_station"
    return None


def facilities(raw: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    raw = raw.assign(ftype=[facility_type(r) for _, r in raw.iterrows()])
    raw = raw[raw["ftype"].notna()]
    area = raw.to_crs(UTM).area
    rows = [{
        "asset_id": f"fac_osm_{r['ftype']}_{osm_ref(r)}", "asset_type": r["ftype"], "name": clean(r.get("name")),
        "confidence": "high" if clean(r.get("name")) else "med",
        "assumptions": "point = representative point of OSM footprint" if r.geometry.geom_type in POLY else "",
        "attrs": {"footprint_m2": round(a, 1) if r.geometry.geom_type in POLY else None,
                  "beds": r.get("beds"), "operator": r.get("operator"), "healthcare": r.get("healthcare"),
                  "emergency": r.get("emergency"), "osm_id": osm_ref(r)},
    } for (_, r), a in zip(raw.iterrows(), area)]
    return gpd.GeoDataFrame(rows, geometry=list(raw.representative_point()), crs=4326)


def tagged(raw: gpd.GeoDataFrame, prefix: str, key: str, keep: list[str], fallback: str | None = None) -> gpd.GeoDataFrame:
    rows = []
    for _, r in raw.iterrows():
        t = clean(r.get(key)) or (clean(r.get(fallback)) if fallback else None)
        rows.append({
            "asset_id": f"{prefix}_osm_{osm_ref(r)}", "asset_type": t or key, "name": clean(r.get("name")),
            "confidence": "high", "assumptions": "",
            "attrs": {**{k: r.get(k) for k in keep}, "osm_id": osm_ref(r)},
        })
    return gpd.GeoDataFrame(rows, geometry=list(raw.geometry), crs=4326)


def main(raw_dir: str | None = None) -> None:
    raw = Path(raw_dir) if raw_dir else max(p.parent for p in (ROOT / "data" / "raw" / "osm").glob("*/meta.json"))
    meta = json.loads((raw / "meta.json").read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    bnd = gpd.read_file(ROOT / "data" / "curated" / "boundary.geojson")
    poly = bnd.geometry.iloc[0]
    read = lambda n: gpd.read_file(raw / f"{n}.gpkg", layer=n)  # noqa: E731

    layers = {
        "buildings": (buildings(read("buildings")), True),
        "roads": (roads(raw / "drive.graphml"), False),
        "facilities": (facilities(read("amenities")), False),
        "waterways": (tagged(read("waterways"), "wtr", "waterway", ["waterway", "natural", "water", "wetland",
                                                                     "intermittent", "width"], "natural"), False),
        "landuse": (tagged(read("landuse"), "lu", "landuse", ["landuse"]), True),
        "osm_power": (tagged(read("power"), "pwr", "power", ["power", "voltage", "operator", "ref", "substation"]),
                      False),
    }
    GPKG.parent.mkdir(parents=True, exist_ok=True)
    GPKG.unlink(missing_ok=True)
    bnd.assign(observed_at=None, attrs=json.dumps({"area_km2": float(bnd["area_km2"].iloc[0])}), in_pilot=True,
               ingested_at=now)[CORE + ["geometry"]].to_file(GPKG, layer="boundary", driver="GPKG",
                                                                  layer_options=NO_INDEX)
    print(f"{'layer':<11}{'total':>7}{'in_pilot':>9}")
    for name, (gdf, polygonal) in layers.items():
        gdf = finish(gdf, poly, polygonal, meta, now)
        if name in PILOT_ONLY:  # D-18: keep the committed GPKG < 5 MB; buffer buildings stay in data/raw
            gdf = gdf[gdf["in_pilot"]]
        gdf.to_file(GPKG, layer=name, driver="GPKG", layer_options=NO_INDEX)
        print(f"{name:<11}{len(gdf):>7}{int(gdf['in_pilot'].sum()):>9}")
    print("wrote", GPKG.relative_to(ROOT), "from", raw.relative_to(ROOT))


if __name__ == "__main__":
    main(*sys.argv[1:])
