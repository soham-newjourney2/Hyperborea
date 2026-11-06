"""P05: Open-Meteo parsing, cache + stale fallback, climate summary, presets."""
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.core.paths import PROCESSED
from backend.app.main import app
from backend.app.services import weather as w

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "openmeteo_forecast.json").read_text(encoding="utf-8"))


def boom(*_):
    raise httpx.ConnectError("offline")


def test_parse_fixture(tmp_path):
    out = w.get_weather(22.57, 88.43, fetch=lambda *_: FIXTURE, cache=tmp_path / "c.json", snapshot=tmp_path / "s.json")
    assert out["origin"] == "live" and out["stale"] is False
    assert out["current"]["condition"] == "Rain" and out["current"]["temperature_2m"] == 27.5
    assert [h["precipitation"] for h in out["hourly"]] == [0.0, 1.2, 3.4]
    assert out["source_id"] == "om_forecast" and out["data_status"] == "modelled"


def test_cache_is_reused(tmp_path):
    c, s = tmp_path / "c.json", tmp_path / "s.json"
    w.get_weather(0, 0, fetch=lambda *_: FIXTURE, cache=c, snapshot=s)
    out = w.get_weather(0, 0, fetch=boom, cache=c, snapshot=s)  # fresh cache → no fetch
    assert out["origin"] == "cache" and out["stale"] is False


def test_fallback_to_snapshot_when_httpx_raises(tmp_path):
    snap = tmp_path / "s.json"
    snap.write_text(json.dumps({"fetched_at": "2026-11-06T10:00:00+00:00", "fetched_ts": 0, "raw": FIXTURE}))
    out = w.get_weather(0, 0, fetch=boom, cache=tmp_path / "missing.json", snapshot=snap)
    assert out["stale"] is True and out["origin"] == "snapshot" and "ConnectError" in out["stale_reason"]
    assert out["fetched_at"] == "2026-11-06T10:00:00+00:00"


def test_no_fallback_raises(tmp_path):
    with pytest.raises(w.WeatherUnavailable):
        w.get_weather(0, 0, fetch=boom, cache=tmp_path / "a.json", snapshot=tmp_path / "b.json")


@pytest.mark.skipif(not (PROCESSED / "climate_summary.json").exists(), reason="run pipelines.climate first")
def test_climate_summary_values():
    s = TestClient(app).get("/api/climate/summary").json()
    first, last = s["period"]["full_years"]
    years = [y["year"] for y in s["years"]]
    assert first == 1981 and years == list(range(first, last + 1)) and s["period"]["n_years"] == len(years)
    for y in s["years"]:
        assert y["total_mm"] >= y["jjas_mm"] >= 0 and y["max_1day_mm"] >= 0
        assert y["heavy_days"] >= y["very_heavy_days"] >= y["extremely_heavy_days"] >= 0
    assert s["data_status"] == "modelled" and s["source_id"] == "om_archive"


@pytest.mark.skipif(not (PROCESSED / "climate_summary.json").exists(), reason="run pipelines.climate first")
def test_presets():
    p = {x["id"]: x for x in TestClient(app).get("/api/scenarios/presets").json()}
    assert {"moderate", "heavy", "extreme", "record_day"} <= p.keys()
    assert p["heavy"]["rain_mm_h"] == 40 and p["heavy"]["total_mm"] == 80
    assert p["record_day"]["total_mm"] == pytest.approx(p["record_day"]["rain_mm_h"] * 6, abs=0.5)
    assert all(x["data_status"] == "simulated" for x in p.values())
