"""P06 step 1: Copernicus DEM GLO-30 (or, P18, EA LiDAR DTM for England) for pilot + buffer → local/rasters/dem.tif.

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


EA_WCS = "https://environment.data.gov.uk/spatialdata/lidar-composite-digital-terrain-model-dtm-1m/wcs"
EA_COVERAGE = "13787b9a-26a4-4775-8523-806d13af58fc__Lidar_Composite_Elevation_DTM_1m"
EA_RES_M = 5.0  # 1 m composite resampled to 5 m by the server (SCALEFACTOR) — plenty for drain slopes


def ea_lidar(area) -> xr.DataArray:
    """EA LIDAR Composite DTM 2022 (OGL v3) over the buffered area, EPSG:27700 → EPSG:4326, in 1.5 km tiles."""
    import io

    import httpx
    x0, y0, x1, y1 = area.to_crs(27700).total_bounds
    step = 1500.0
    tiles = []
    with httpx.Client(timeout=180, headers={"User-Agent": "Hyperborea/0.1"}) as c:
        for x in range(int(x0 // step), int(x1 // step) + 1):
            for y in range(int(y0 // step), int(y1 // step) + 1):
                ex, ny = x * step, y * step
                r = c.get(EA_WCS, params=[("service", "WCS"), ("version", "2.0.1"), ("request", "GetCoverage"),
                                          ("coverageId", EA_COVERAGE), ("format", "image/tiff"),
                                          ("subset", f"E({ex},{ex + step})"), ("subset", f"N({ny},{ny + step})"),
                                          ("SCALEFACTOR", str(1 / EA_RES_M))])
                r.raise_for_status()
                if "tiff" not in r.headers.get("content-type", ""):
                    raise RuntimeError(f"EA WCS returned {r.headers.get('content-type')}: {r.text[:200]}")
                da = xr.open_dataarray(io.BytesIO(r.content), engine="rasterio").squeeze(drop=True)
                tiles.append(da.where(da > -1000))
    print(f"  {len(tiles)} EA LiDAR tile(s) at {EA_RES_M:.0f} m")
    dem = merge_arrays(tiles).rio.write_crs(27700)
    return dem.rio.reproject(4326, nodata=-9999.0)


def main() -> None:
    bnd = gpd.read_file(R.data_dir("curated") / "boundary.geojson")
    area = bnd.to_crs(R.metric_crs()).buffer(BUFFER_M).to_crs(4326)
    w, s, e, n = area.total_bounds
    if R.cfg().get("dem") == "ea_lidar_dtm":
        dem = ea_lidar(area)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        dem.rio.to_raster(OUT, compress="deflate")
        v = dem.where(dem > -100)
        print(f"  wrote {OUT.relative_to(ROOT)} {dem.shape} px; elevation min {float(v.min()):.1f} "
              f"median {float(v.median()):.1f} max {float(v.max()):.1f} m (EA LiDAR DTM, bare earth)")
        return
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
