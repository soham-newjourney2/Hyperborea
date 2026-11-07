"""P06 step 1: Copernicus DEM GLO-30 for pilot + buffer → local/rasters/dem.tif (not committed).

Run:  python -m pipelines.fetch_dem
"""
from __future__ import annotations

import geopandas as gpd
import planetary_computer
import pystac_client
import rioxarray  # noqa: F401  (registers .rio)
import xarray as xr
from rioxarray.merge import merge_arrays

from pipelines.osm_common import ROOT
from backend.app.core import regions as R  # noqa: E402  (P16: HYPERBOREA_REGION → paths, CRS, timezone)

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
BUFFER_M = 2000
OUT = R.local_dir("rasters") / "dem.tif"


def main() -> None:
    bnd = gpd.read_file(R.data_dir("curated") / "boundary.geojson")
    area = bnd.to_crs(R.metric_crs()).buffer(BUFFER_M).to_crs(4326)
    w, s, e, n = area.total_bounds
    cat = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)
    items = list(cat.search(collections=["cop-dem-glo-30"], bbox=[w, s, e, n]).items())
    print(f"  {len(items)} DEM tile(s): {[i.id for i in items]}")
    arrays = [xr.open_dataarray(i.assets["data"].href, engine="rasterio").squeeze(drop=True)
              .rio.clip_box(w, s, e, n) for i in items]
    dem = arrays[0] if len(arrays) == 1 else merge_arrays(arrays)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    dem.rio.to_raster(OUT, compress="deflate")
    v = dem.where(dem > -100)
    print(f"  wrote {OUT.relative_to(ROOT)} {dem.shape} px; elevation min {float(v.min()):.1f} "
          f"median {float(v.median()):.1f} max {float(v.max()):.1f} m")


if __name__ == "__main__":
    main()
