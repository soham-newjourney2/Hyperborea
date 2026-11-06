"""P02 step 2: save the user-chosen candidate as the pilot boundary (D-17).

Run:  python -m pipelines.make_boundary [candidate]   (default: sector_v)
Out:  data/curated/boundary.geojson
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

import geopandas as gpd
from shapely.geometry import MultiPolygon

from pipelines.osm_common import ROOT

UTM = 32645
MIN_PART_SHARE = 0.02  # drop slivers < 2 % of the largest part (road-cell artefacts)


def main(candidate: str = "sector_v") -> None:
    cands = gpd.read_file(ROOT / "data" / "curated" / "candidates.geojson")
    row = cands[cands["candidate"] == candidate]
    if row.empty:
        raise SystemExit(f"unknown candidate {candidate!r}; have {list(cands['candidate'])}")
    geom = gpd.GeoSeries(row.geometry.values, crs=4326).to_crs(UTM).iloc[0]
    parts = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    big = max(p.area for p in parts)
    kept = [p for p in parts if p.area >= MIN_PART_SHARE * big]
    geom = kept[0] if len(kept) == 1 else MultiPolygon(kept)
    print(f"{candidate}: kept {len(kept)}/{len(parts)} parts, {geom.area / 1e6:.2f} km²")

    out = gpd.GeoDataFrame({
        "asset_id": [f"bnd_cur_{candidate}"],
        "asset_type": ["pilot_boundary"],
        "name": ["Salt Lake " + candidate.replace("sector_", "Sector ").replace("_", " + ").upper().replace("SECTOR", "Sector")],
        "data_status": ["curated"],
        "source_id": ["cur_boundary"],
        "ingested_at": [datetime.now(timezone.utc).isoformat(timespec="seconds")],
        "confidence": ["med"],
        "assumptions": ["Sector outline built from OSM road cells assigned to Salt Lake block labels; not an official boundary"],
        "area_km2": [round(geom.area / 1e6, 3)],
    }, geometry=[geom], crs=UTM).to_crs(4326)
    path = ROOT / "data" / "curated" / "boundary.geojson"
    out.to_file(path, driver="GeoJSON")
    print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main(*sys.argv[1:])
