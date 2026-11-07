"""P02: provenance + geometry integrity of data/processed/hyperborea.gpkg."""
import json
import re

import geopandas as gpd
import pyogrio
import pytest

from backend.app.core.paths import GPKG, ROOT
from backend.app.core.provenance import DataStatus, FeatureProps

LAYERS = ["boundary", "buildings", "roads", "facilities", "waterways", "landuse", "osm_power",
          "drains", "drain_nodes", "outfalls", "catchments", "substations", "transformers", "feeders", "cv_water"]
REQUIRED = ["asset_id", "asset_type", "data_status", "source_id", "ingested_at"]

pytestmark = pytest.mark.skipif(not GPKG.exists(), reason="run pipelines.normalize_osm first")


FILES = [GPKG] + sorted(p for p in GPKG.parent.glob("*.gpkg") if p != GPKG)
WHERE = {n: f for f in FILES if f.exists() for n, _ in pyogrio.list_layers(f)}


@pytest.fixture(scope="module")
def layers() -> dict[str, gpd.GeoDataFrame]:
    return {n: gpd.read_file(WHERE[n], layer=n) for n in LAYERS}


def test_all_layers_present():
    assert set(LAYERS) <= set(WHERE)


def test_each_gpkg_under_5mb():  # planning §5 commit rule
    for f in FILES:
        assert f.stat().st_size < 5 * 1024 * 1024, f"{f.name} is {f.stat().st_size / 1e6:.1f} MB"


def test_required_props_present(layers):
    sources = set(re.findall(r"^### (\S+)", (ROOT / "docs" / "DATA_SOURCES.md").read_text(encoding="utf-8"), re.M))
    for name, gdf in layers.items():
        assert len(gdf), name
        for col in REQUIRED:
            assert gdf[col].notna().all(), f"{name}.{col} has nulls"
        assert set(gdf["data_status"]) <= {s.value for s in DataStatus}, name
        assert set(gdf["source_id"]) <= sources, f"{name}: source_id not registered in DATA_SOURCES"


def test_props_match_shared_schema(layers):
    for name, gdf in layers.items():
        for rec in gdf.drop(columns="geometry").head(200).to_dict("records"):
            rec["attrs"] = json.loads(rec["attrs"])
            FeatureProps(**{k: (None if v != v else v) for k, v in rec.items() if k != "in_pilot"})  # NaN → None


def test_asset_ids_unique(layers):
    ids = gpd.pd.concat([g["asset_id"] for g in layers.values()])
    assert ids.is_unique, ids[ids.duplicated()].head().tolist()


def test_geometries_valid(layers):
    for name, gdf in layers.items():
        assert gdf.geometry.notna().all() and not gdf.geometry.is_empty.any(), name
        assert gdf.is_valid.all(), f"{name}: {int((~gdf.is_valid).sum())} invalid"


def test_pilot_features_within_boundary(layers):
    bnd = layers["boundary"].to_crs(32645).buffer(1.0).iloc[0]
    for name, gdf in layers.items():
        pilot = gdf[gdf["in_pilot"].astype(bool)].to_crs(32645)
        # Lines: must touch the pilot (a line's representative vertex is unstable for edge roads under
        # reversal/reprojection). Points/polygons: representative point inside.
        lines = pilot.geom_type.str.contains("Line")
        assert pilot[lines].intersects(bnd).all(), name
        assert pilot[~lines].representative_point().within(bnd).all(), name


def test_buildings_have_height(layers):
    attrs = layers["buildings"]["attrs"].map(json.loads)
    assert attrs.map(lambda a: a["height_m"] > 0).all()
    assert set(attrs.map(lambda a: a["height_status"])) <= {"observed", "modelled", "assumed"}
    assert layers["buildings"]["in_pilot"].astype(bool).sum() > 500
