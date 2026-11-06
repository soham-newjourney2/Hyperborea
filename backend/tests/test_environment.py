"""P11: NAQI maths, land-cover shares, water records, AQ fallback."""
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.core.paths import PROCESSED
from backend.app.main import app
from backend.app.services import air

client = TestClient(app)
RAW = {"latitude": 22.6, "longitude": 88.4, "hourly_units": {"pm2_5": "µg/m³"},
       "hourly": {"time": [f"2026-11-06T{h:02d}:00" for h in range(24)],
                  "pm2_5": [100.0] * 24, "pm10": [120.0] * 24, "nitrogen_dioxide": [30.0] * 24, "ozone": [40.0] * 24}}


@pytest.mark.parametrize("pol,conc,aqi,cat", [
    ("pm2_5", 0, 0, "Good"), ("pm2_5", 30, 50, "Good"), ("pm2_5", 60, 100, "Satisfactory"),
    ("pm2_5", 90, 200, "Moderate"), ("pm2_5", 120, 300, "Poor"), ("pm2_5", 250, 400, "Very Poor"),
    ("pm2_5", 300, 421, "Severe"), ("pm10", 100, 100, "Satisfactory"), ("pm10", 250, 200, "Moderate"),
])
def test_naqi_sub_index_and_category(pol, conc, aqi, cat):
    assert air.sub_index(pol, conc) == aqi and air.category(aqi)["name"] == cat


def test_summary_takes_max_sub_index():
    s = air.summarise(RAW, now_local="2026-11-06T23:00")
    assert s["means_ugm3"]["pm2_5"] == 100 and s["dominant"] == "pm2_5" and s["category"] == "Poor"
    assert s["naqi"] == max(v for v in s["sub_index"].values() if v is not None)


def boom(*_):
    raise httpx.ConnectError("offline")


def test_air_fallback_to_snapshot(tmp_path: Path):
    snap = tmp_path / "s.json"
    snap.write_text(json.dumps({"fetched_at": "2026-11-06T10:00:00+00:00", "fetched_ts": 0, "raw": RAW}))
    out = air.get_air(0, 0, fetch=boom, cache=tmp_path / "none.json", snapshot=snap)
    assert out["stale"] and out["origin"] == "snapshot" and out["data_status"] == "modelled"
    with pytest.raises(air.AirUnavailable):
        air.get_air(0, 0, fetch=boom, cache=tmp_path / "a.json", snapshot=tmp_path / "b.json")


@pytest.mark.skipif(not (PROCESSED / "landcover_stats.json").exists(), reason="run pipelines.landcover")
def test_landcover_shares_sum_to_100():
    s = client.get("/api/environment/landcover").json()
    assert sum(s["worldcover"]["pilot_shares_pct"].values()) == pytest.approx(100, abs=0.5)
    for c in list(s["per_catchment"].values())[:100]:
        assert 0 <= c["built_up_pct"] <= 100 and 0 <= c["green_pct"] <= 100
    assert -1 <= s["ndvi"]["pilot_mean"] <= 1 and len(s["overlays"]["ndvi"]["bounds"]) == 4


def test_water_points_have_units_dates_and_status():
    r = client.get("/api/environment/water")
    if r.status_code == 503:
        pytest.skip("run pipelines.make_water_demo")
    body = r.json()
    for f in body["points"]["features"]:
        a = f["properties"]["attrs"]
        assert a["sample_date"] and all(p["unit"] and p["value"] is not None for p in a["parameters"])
        assert f["properties"]["data_status"] in {"simulated", "curated"} and f["geometry"]["type"] == "Point"
    if body["demo"]:
        assert "DEMO DATA" in body["banner"]
