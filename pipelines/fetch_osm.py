"""P02 step 3: fetch raw OSM for the pilot boundary + 2 km buffer.

Raw output is immutable: each run writes a new timestamped folder.
Run:  python -m pipelines.fetch_osm [pbf|overpass]   (default pbf = Geofabrik extract, see osm_pbf.py)
Out:  data/raw/osm/<YYYYmmddTHHMMSSZ>/{buildings,amenities,power,waterways,landuse}.gpkg,
      drive.graphml, walk.graphml, meta.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import geopandas as gpd
import osmnx as ox
import pandas as pd

from pipelines import osm_pbf
from pipelines.osm_common import ROOT, overpass

UTM = 32645
BUFFER_M = 2000
TILE_M2 = 4e6  # public Overpass mirrors time out on the full ~30 km² building query
LAYERS = {
    "buildings": {"building": True},
    "amenities": {
        "amenity": ["hospital", "clinic", "school", "college", "university", "fire_station", "police"],
        "railway": ["station", "halt"],
        "station": ["subway"],
    },
    "power": {"power": True},
    "waterways": {"waterway": True, "natural": ["water", "wetland"]},
    "landuse": {"landuse": True},
}


def sanitize(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Make an osmnx GeoDataFrame writable to GPKG: flat index, string non-scalars, unique columns."""
    gdf = gdf.reset_index()
    seen, keep = set(), []
    for c in gdf.columns:  # SQLite column names are case-insensitive
        if c.lower() not in seen:
            seen.add(c.lower())
            keep.append(c)
    gdf = gdf[keep]
    for c in gdf.columns:
        if c != "geometry" and gdf[c].dtype == object:
            gdf[c] = gdf[c].map(lambda v: v if v is None or isinstance(v, str) or pd.isna(v) else str(v)
                                if not isinstance(v, (list, dict)) else json.dumps(v))
    return gdf


def main(source: str = "pbf") -> None:
    boundary = gpd.read_file(ROOT / "data" / "curated" / "boundary.geojson")
    area = boundary.to_crs(UTM).buffer(BUFFER_M).to_crs(4326).union_all()
    stamp = datetime.now(timezone.utc)
    final = ROOT / "data" / "raw" / "osm" / stamp.strftime("%Y%m%dT%H%M%SZ")
    out = final.with_name(final.name + ".partial")  # renamed only when complete
    out.mkdir(parents=True, exist_ok=False)
    ox.settings.max_query_area_size = TILE_M2  # split into small Overpass queries (cached per tile)

    if source == "pbf":
        pbf = osm_pbf.ensure_pbf()
        xml = osm_pbf.clip(pbf, area.bounds, out)
        access = {"via": "geofabrik_pbf", "url": osm_pbf.PBF_URL, "osm_data_at": "2026-11-05T14:54:52+00:00"}
        features = lambda tags: ox.features_from_xml(xml["features"], polygon=area, tags=tags)  # noqa: E731

        def graph(net):
            g = ox.graph_from_xml(xml[net], bidirectional=net == "walk", simplify=False, retain_all=True)
            return ox.simplify_graph(ox.truncate.truncate_graph_polygon(g, area))
    else:
        access = {"via": "overpass", "url": ox.settings.overpass_url, "osm_data_at": stamp.isoformat(timespec="seconds")}
        features = lambda tags: overpass(ox.features_from_polygon, area, tags=tags)  # noqa: E731
        graph = lambda net: overpass(ox.graph_from_polygon, area, network_type=net, retain_all=True)  # noqa: E731

    counts = {}
    for name, tags in LAYERS.items():
        gdf = features(tags)
        sanitize(gdf).to_file(out / f"{name}.gpkg", layer=name, driver="GPKG")
        counts[name] = len(gdf)
        print(f"  {name}: {len(gdf)}", flush=True)

    for net in ("drive", "walk"):
        g = graph(net)
        ox.save_graphml(g, out / f"{net}.graphml")
        counts[f"{net}_edges"] = g.number_of_edges()
        print(f"  {net}: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges", flush=True)

    meta = {
        "source_id": "osm",
        "fetched_at": stamp.isoformat(timespec="seconds"),
        "boundary": boundary["asset_id"].iloc[0],
        "buffer_m": BUFFER_M,
        "bbox_4326": list(area.bounds),
        "osmnx": ox.__version__,
        **access,
        "tags": LAYERS,
        "counts": counts,
        "licence": "ODbL 1.0 — © OpenStreetMap contributors",
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    out.rename(final)
    print("wrote", final.relative_to(ROOT))


if __name__ == "__main__":
    main(*sys.argv[1:])
