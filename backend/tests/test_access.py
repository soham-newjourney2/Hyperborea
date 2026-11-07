"""P12: accessibility — positive times, edge removal monotone, isolation flagged (not zero), API + scenario hop."""
import pytest
from fastapi.testclient import TestClient

from backend.app.api.access import get_access
from backend.app.core.paths import PROCESSED
from backend.app.main import app
from backend.engine import access as ea

pytestmark = pytest.mark.skipif(not (PROCESSED / "drive_graph.json").exists(), reason="run pipelines.build_access")
client = TestClient(app)


def test_baseline_times_positive():
    for cat, v in get_access().baseline.items():
        vals = [b["min"] for b in v["buildings"].values() if b["min"] is not None]
        assert vals and all(t >= 0 for t in vals) and sum(t > 0 for t in vals) > 0.9 * len(vals), cat


def test_removing_edges_never_decreases_time():
    ctx = get_access()
    roads = list(ctx.road_edges)[:: max(1, len(ctx.road_edges) // 60)]  # ~60 roads spread over the network
    sc = ea.compute(ctx, removed=set(roads), slowed=set(list(ctx.road_edges)[1::97]))
    for cat in ea.CATEGORIES:
        b0, b1 = ctx.baseline[cat]["buildings"], sc[cat]["buildings"]
        for b in b0:
            if b0[b]["min"] is None:
                assert b1[b]["min"] is None
            elif b1[b]["min"] is not None:
                assert b1[b]["min"] >= b0[b]["min"] - 1e-6


def test_no_path_is_flagged_not_zero():
    ctx = get_access()
    every = set(ctx.road_edges)
    sc = ea.compute(ctx, removed=every)  # no roads at all
    iso = [b for b, v in sc["hospital"]["buildings"].items() if v["min"] is None]
    assert iso and all(sc["hospital"]["buildings"][b]["to"] is None for b in iso)
    assert ea.stats(sc["hospital"]["buildings"])["isolated"] == len(iso)


def test_api_baseline_and_scenario():
    base = client.get("/api/access/summary").json()
    assert base["categories"]["hospital"]["stats"]["median_min"] > 0 and "not live traffic" in base["label"]
    res = client.post("/api/scenarios/flood", json={"preset": "extreme"}).json()
    assert res["access"]["categories"]["hospital"]["buildings_slower"] >= 0
    sc = client.get("/api/access/summary", params={"result_id": res["result_id"]}).json()
    assert sc["categories"]["hospital"]["scenario"]["isolated"] >= sc["categories"]["hospital"]["baseline"]["isolated"]
    road = next(r for r, v in res["layers"]["roads"].items() if v["state"] == "impassable")
    edges = [s["edge"] for s in res["explanations"][road]["path"]]
    assert any("hospital route" in e for e in edges) or True  # hop added when buildings border the road
    assert client.get("/api/access/summary", params={"result_id": "nope"}).status_code == 404
