"""P16: curated study rectangle for a non-default region (config/regions.yaml `bbox`) → boundary.geojson.

Run:  $env:HYPERBOREA_REGION='chennai_velachery'; python -m pipelines.make_region_boundary
Out:  data/curated/regions/<id>/boundary.geojson (same schema as the Sector V boundary)
"""
from datetime import datetime, timezone

import geopandas as gpd
from shapely.geometry import box

from backend.app.core import regions as R


def main() -> None:
    rid = R.current()
    if rid == R.DEFAULT:
        raise SystemExit("Sector V uses pipelines.make_boundary — set HYPERBOREA_REGION to a new region id")
    c = R.cfg(rid)
    geom = gpd.GeoSeries([box(*c["bbox"])], crs=4326).to_crs(R.metric_crs(rid)).iloc[0]
    out = gpd.GeoDataFrame({
        "asset_id": [f"bnd_cur_{rid}"],
        "asset_type": ["pilot_boundary"],
        "name": [f"{c['name']}, {c['city']}"],
        "data_status": ["curated"],
        "source_id": ["cur_boundary"],
        "ingested_at": [datetime.now(timezone.utc).isoformat(timespec="seconds")],
        "confidence": ["low"],
        "assumptions": ["Study rectangle chosen for the pilot (config/regions.yaml), not an official or ward boundary"],
        "area_km2": [round(geom.area / 1e6, 3)],
    }, geometry=[geom], crs=R.metric_crs(rid)).to_crs(4326)
    path = R.data_dir("curated", rid) / "boundary.geojson"
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_file(path, driver="GeoJSON")
    print(f"{rid}: {geom.area / 1e6:.2f} km² → {path}")


if __name__ == "__main__":
    main()
