"""P16 multi-region core: registry valid, ?region= scoping, unknown → 404, default behaviour unchanged."""
import math

from fastapi.testclient import TestClient

from backend.app.core import regions as R
from backend.app.core.paths import DATA
from backend.app.main import app

client = TestClient(app)


def _utm_epsg(lon: float, lat: float) -> int:
    return (32600 if lat >= 0 else 32700) + int(math.floor((lon + 180) / 6)) + 1


def test_registry_valid():
    reg = R.registry()
    assert R.DEFAULT == "sector_v" and R.DEFAULT in reg and len(reg) >= 5
    for rid, r in reg.items():
        for k in ("name", "city", "country", "timezone", "metric_crs", "aq_index", "design_storm_mm_h"):
            assert r.get(k) not in (None, ""), (rid, k)
        if rid == R.DEFAULT:
            continue
        x0, y0, x1, y1 = r["bbox"]
        assert x0 < x1 and y0 < y1, rid
        assert _utm_epsg((x0 + x1) / 2, (y0 + y1) / 2) == r["metric_crs"], rid
        w = (x1 - x0) * 111.32 * math.cos(math.radians((y0 + y1) / 2))
        assert 1.5 <= w * (y1 - y0) * 110.57 <= 5.0, f"{rid}: study area should be ~3 km²"


def test_data_dirs():
    assert R.data_dir("processed", "sector_v") == DATA / "regions" / "sector_v" / "processed"  # one folder per region
    assert R.data_dir("curated", "pune_kharadi") == DATA / "regions" / "pune_kharadi" / "curated"
    assert R.metric_crs("sector_v") == 32645


def test_region_param_scopes_request():
    assert client.get("/api/health").json()["region"] == "sector_v"
    assert client.get("/api/health", params={"region": "london_stratford"}).json()["region"] == "london_stratford"
    r = client.get("/api/health", params={"region": "atlantis"})
    assert r.status_code == 404 and "atlantis" in r.json()["detail"]


def test_regions_endpoint():
    body = client.get("/api/regions").json()
    ids = {r["id"]: r for r in body["regions"]}
    assert body["default"] == "sector_v" and ids["sector_v"]["status"] == "ready" and ids["sector_v"]["default"]
    assert {"chennai_velachery", "pune_kharadi", "london_stratford", "sydney_green_square"} <= ids.keys()


def test_default_region_unchanged_and_other_region_isolated():
    a = client.get("/api/layers").json()
    assert a == client.get("/api/layers", params={"region": "sector_v"}).json() and len(a) >= 10
    missing = [rid for rid in R.registry() if not R.is_ready(rid)]
    if missing:  # a region without data serves nothing from Sector V
        assert client.get("/api/layers", params={"region": missing[0]}).json() == []
        assert client.get("/api/region", params={"region": missing[0]}).status_code == 503


def test_per_region_cache_isolated():
    calls = []

    @R.per_region
    def loader():
        calls.append(R.current())
        return object()

    first = loader()
    tok = R.set_current("pune_kharadi")
    try:
        other = loader()
        assert loader() is other
    finally:
        R.reset(tok)
    assert loader() is first and other is not first and calls == ["sector_v", "pune_kharadi"]


def test_every_ready_region_serves_the_full_stack():
    """P17: each built region has the core layers, a heavy flood, access, a development comparison and its own CRS."""
    need = {"boundary", "buildings", "roads", "facilities", "drains", "catchments", "outfalls", "transformers", "sites"}
    for rid in [r for r in R.registry() if R.is_ready(r)]:
        q = {"region": rid}
        ids = {m["id"] for m in client.get("/api/layers", params=q).json()}
        assert need <= ids, (rid, need - ids)
        res = client.post("/api/scenarios/flood", params=q, json={"preset": "heavy"}).json()
        assert 0 < res["summary"]["drains_overloaded"] < res["summary"]["drains_total"], rid
        assert client.get("/api/access/summary", params=q).status_code == 200, rid
        cmp = client.post("/api/development/compare", params=q, json={"options": [{"site_id": "S1"}, {"site_id": "S2"}]})
        assert cmp.status_code == 200 and "approved" not in str(cmp.json()["verdicts"]).lower(), rid
        assert client.get("/api/region", params=q).json()["asset_id"].endswith(rid if rid != R.DEFAULT else "sector_v")
