"""P03: /region, /layers, /layers/{id}, /assets/{id}."""
import pytest
from fastapi.testclient import TestClient

from backend.app.core.paths import GPKG
from backend.app.main import app

pytestmark = pytest.mark.skipif(not GPKG.exists(), reason="run pipelines.normalize_osm first")
client = TestClient(app)


def test_region():
    r = client.get("/api/region")
    assert r.status_code == 200
    body = r.json()
    w, s, e, n = body["bbox"]
    assert w < body["centroid"][0] < e and s < body["centroid"][1] < n
    assert body["boundary"]["features"][0]["properties"]["data_status"] == "curated"


def test_layers_registry():
    r = client.get("/api/layers")
    assert r.status_code == 200
    meta = {m["id"]: m for m in r.json()}
    assert {"boundary", "buildings", "roads", "facilities"} <= meta.keys()
    b = meta["buildings"]
    assert b["count"] >= b["count_in_pilot"] > 0 and b["source_ids"] == ["osm"]
    assert sum(b["data_status"].values()) == b["count"]


def test_buildings_geojson():
    full = client.get("/api/layers/buildings").json()
    pilot = client.get("/api/layers/buildings", params={"in_pilot": True})
    assert pilot.headers["content-type"].startswith("application/geo+json")
    feats = pilot.json()["features"]
    assert 0 < len(feats) <= len(full["features"])  # buildings are pilot-only since D-18
    p = feats[0]["properties"]
    assert p["in_pilot"] is True and p["attrs"]["height_m"] > 0
    assert {"asset_id", "data_status", "source_id"} <= p.keys()


def test_unknown_layer_404():
    assert client.get("/api/layers/nope").status_code == 404


def test_asset_detail_and_404():
    aid = client.get("/api/layers/facilities").json()["features"][0]["properties"]["asset_id"]
    r = client.get(f"/api/assets/{aid}")
    assert r.status_code == 200
    body = r.json()
    assert body["asset_id"] == aid and body["layer"] == "facilities" and isinstance(body["relationships"], list)
    assert len(body["position"]) == 2
    assert client.get("/api/assets/bld_osm_w0").status_code == 404
