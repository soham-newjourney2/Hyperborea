"""P02 step 1: build candidate pilot boundaries from OSM and print a comparison table.

Sector outlines don't exist in OSM as polygons, so we construct them (data_status=curated):
polygonize the road network into cells, assign each cell to its nearest Salt Lake block label
(place=neighbourhood / city_block), and dissolve the cells of the blocks that make up a sector.

Run:  python -m pipelines.scan_candidates
Out:  data/curated/candidates.geojson + table on stdout
"""
from __future__ import annotations

import geopandas as gpd
import osmnx as ox
import pandas as pd
from shapely.geometry import box
from shapely.ops import polygonize, unary_union

from pipelines.osm_common import ROOT, overpass
from backend.app.core import regions as R  # noqa: E402

UTM = 32645
# Block membership from the Salt Lake block grid, checked against the OSM "Sector III"
# admin line (way 156279886) and building addr tags (P02 scan, 2026-11-06).
SECTOR_BLOCKS = {
    "III": "FC FD FE FF GA GB GC GD GE HA HB IA IB IC JB JC JD KA KB KC LA".split(),
    "V": "AN AP AQ BN CN CP DN DP EM EN GN GP HM".split(),
}
# Study window around Sectors III + V (keeps Overpass queries small).
WINDOW = box(88.398, 22.553, 88.452, 22.592)
MAX_LABEL_M = 450
CANDIDATES = {"sector_iii": ["III"], "sector_v": ["V"], "sector_iii_v": ["III", "V"]}

FAC_TAGS = {
    "amenity": ["hospital", "clinic", "school", "college", "university", "fire_station", "police"],
    "railway": ["station", "halt", "subway_entrance"],
    "station": ["subway"],
    "power": True,
    "waterway": True,
}
DRIVE = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential",
         "living_street", "service", "motorway_link", "trunk_link", "primary_link", "secondary_link",
         "tertiary_link"}


def block_labels(city) -> gpd.GeoDataFrame:
    pl = overpass(ox.features_from_polygon, city, tags={"place": True})
    pl = pl[pl["name"].fillna("").str.fullmatch(r"[A-Z]{2} Block")]
    pts = pl.assign(block=pl["name"].str[:2], geometry=pl.geometry.representative_point())
    return pts[["block", "geometry"]].drop_duplicates("block").reset_index(drop=True)


def road_cells(city, roads: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    lines = roads[roads.geom_type.isin(["LineString", "MultiLineString"])].geometry
    noded = unary_union(list(lines) + [city.boundary])
    cells = gpd.GeoDataFrame(geometry=list(polygonize(noded)), crs=4326)
    return cells[cells.representative_point().within(city)].reset_index(drop=True)


def sector_polygons(cells, labels) -> dict[str, object]:
    cu, lu = cells.to_crs(UTM), labels.to_crs(UTM)
    cu["geometry_pt"] = cu.representative_point()
    # Cap the match distance: interior blocks sit <~430 m from their label; without a cap the
    # edge blocks swallow every unlabelled cell up to 2 km away (P02 diagnostic, 2026-11-06).
    j = gpd.sjoin_nearest(cu.set_geometry("geometry_pt"), lu, how="left", max_distance=MAX_LABEL_M)
    cells = cells.assign(block=j.groupby(level=0)["block"].first())
    out = {}
    for sec, blks in SECTOR_BLOCKS.items():
        missing = set(blks) - set(labels["block"])
        if missing:
            print(f"  warning: no OSM label for {sec} blocks {sorted(missing)}")
        g = cells[cells["block"].isin(blks)].to_crs(UTM).buffer(1.0).union_all().buffer(-1.0)
        out[sec] = gpd.GeoSeries([g], crs=UTM).to_crs(4326).iloc[0]
    return out


def stats(poly, buildings, roads, feats) -> dict:
    b = buildings[buildings.representative_point().within(poly)]
    has_h = b.get("height", pd.Series(index=b.index)).notna() | b.get("building:levels", pd.Series(index=b.index)).notna()
    r = roads[roads["highway"].isin(DRIVE)].clip(poly)
    f = feats[feats.representative_point().within(poly)]
    am = f.get("amenity", pd.Series(index=f.index))
    rail = f.get("railway", pd.Series(index=f.index))
    return {
        "area_km2": round(gpd.GeoSeries([poly], crs=4326).to_crs(UTM).area.iloc[0] / 1e6, 2),
        "buildings": len(b),
        "pct_height": round(100 * has_h.mean(), 1) if len(b) else 0,
        "road_km": round(r.to_crs(UTM).length.sum() / 1000, 1),
        "hospital_clinic": int(am.isin(["hospital", "clinic"]).sum()),
        "school_college": int(am.isin(["school", "college", "university"]).sum()),
        "fire": int((am == "fire_station").sum()),
        "police": int((am == "police").sum()),
        "power": int(f.get("power", pd.Series(index=f.index)).notna().sum()),
        "waterway": int(f.get("waterway", pd.Series(index=f.index)).notna().sum()),
        "rail_metro": int(rail.isin(["station", "halt", "subway_entrance"]).sum()),
    }


def main() -> None:
    city = ox.geocode_to_gdf("Bidhannagar").geometry.iloc[0]
    print("fetching OSM (cached after first run)…", flush=True)
    labels = block_labels(city)
    city = city.intersection(WINDOW)
    roads = overpass(ox.features_from_polygon, city, tags={"highway": True})
    print(f"  roads: {len(roads)}", flush=True)
    buildings = overpass(ox.features_from_polygon, city, tags={"building": True})
    print(f"  buildings: {len(buildings)}", flush=True)
    buildings = buildings[buildings.geom_type.isin(["Polygon", "MultiPolygon"])]
    feats = overpass(ox.features_from_polygon, city, tags=FAC_TAGS)
    print(f"  facilities/power/waterways: {len(feats)}", flush=True)

    secs = sector_polygons(road_cells(city, roads), labels)
    rows, geoms = [], []
    for name, parts in CANDIDATES.items():
        poly = unary_union([secs[p] for p in parts])
        rows.append({"candidate": name, **stats(poly, buildings, roads, feats)})
        geoms.append(poly)

    table = pd.DataFrame(rows)
    print(table.to_string(index=False))
    out = R.data_dir("curated", "sector_v") / "candidates.geojson"
    out.parent.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(table.assign(data_status="curated", source_id="osm"), geometry=geoms, crs=4326).to_file(
        out, driver="GeoJSON")
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
