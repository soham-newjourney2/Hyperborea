"""P21 early warning: dry → none; burst → window found + level; endpoint shape."""
import pytest
from fastapi.testclient import TestClient

from backend.app.core.paths import GPKG
from backend.app.main import app
from backend.engine import warning as ew

RULES = {"min_rain_mm_h": 2.0, "windows_h": [1, 2, 3], "probability_floor_pct": 30,
         "levels": {"warning": {"drains_overloaded_pct": 10, "facilities_affected": 1},
                    "watch": {"drains_overloaded_pct": 3, "road_km_impassable": 0.1}}}


def _hours(rain):
    return [{"time": f"2026-11-12T{i:02d}:00", "precipitation": r, "precipitation_probability": 80} for i, r in enumerate(rain)]


def _run(total_drains=100):
    def run(rain, dur):
        n = int(rain * dur / 2)
        return {"result_id": "r1", "affected": [], "summary": {"drains_overloaded": n, "drains_total": total_drains,
                                                               "road_km_impassable": 0.0, "facilities_affected": 0}}
    return run


def test_dry_forecast_is_none_without_engine_run():
    called = []
    out = ew.outlook(_hours([0, 0.5, 1.0] * 24), lambda r, d: 99, lambda r, d: called.append(1), RULES)
    assert out["level"] == "none" and out["window"] is None and not called and len(out["timeline"]) == 72


def test_burst_picks_worst_window_and_levels():
    rain = [0] * 10 + [5, 30, 28, 4] + [0] * 58
    out = ew.outlook(_hours(rain), lambda r, d: int(r), _run(), RULES)  # stand-in surrogate: intensity matters
    w = out["window"]
    assert w["start_time"] == "2026-11-12T11:00" and w["hours"] == 1 and w["rain_mm_h"] == 30.0
    longer = ew.outlook(_hours(rain), lambda r, d: int(r * d), _run(), RULES)["window"]  # volume matters
    assert longer["hours"] == 3 and longer["total_mm"] == 63.0
    assert out["level"] == "warning" and out["reasons"] and "WARNING" in out["headline"]


def test_level_rules():
    assert ew.level_for({"drains_overloaded": 4, "drains_total": 100}, RULES["levels"])[0] == "watch"
    assert ew.level_for({"drains_overloaded": 1, "drains_total": 100}, RULES["levels"])[0] == "none"
    assert ew.level_for({"drains_overloaded": 0, "drains_total": 100, "facilities_affected": 2}, RULES["levels"])[0] == "warning"


@pytest.mark.skipif(not GPKG.with_name("drainage.gpkg").exists(), reason="run P06 pipelines")
def test_endpoint_shape(monkeypatch):
    from backend.app.api import warning as wapi
    fake = {"fetched_at": "2026-11-12T00:00:00+00:00", "stale": False, "hourly": _hours([0] * 20 + [40, 45] + [0] * 50)}
    monkeypatch.setattr(wapi, "_weather", lambda: fake)
    r = TestClient(app).get("/api/warning").json()
    assert r["region"] == "sector_v" and len(r["timeline"]) == 72 and r["window"]["hours"] in (1, 2, 3)
    assert r["level"] in ew.LEVELS and r["summary"]["drains_total"] > 0 and "not an official warning" in r["label"]


@pytest.mark.skipif(not GPKG.with_name("drainage.gpkg").exists(), reason="run P06 pipelines")
def test_demo_burst_is_labelled_simulated(monkeypatch):
    from backend.app.api import warning as wapi
    fake = {"fetched_at": "2026-11-12T01:00:00+00:00", "stale": False, "hourly": _hours([0] * 72)}
    monkeypatch.setattr(wapi, "_weather", lambda: fake)
    r = TestClient(app).get("/api/warning", params={"demo": "true"}).json()
    assert r["demo"] and r["data_status"] == "simulated" and r["label"].startswith("DEMO")
    assert r["window"] is not None and r["peak_rain_mm_h"] == 45.0
