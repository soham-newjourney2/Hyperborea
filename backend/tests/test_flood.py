"""P08: rainfall cascade (VISION §19.3) — capacity, monotonicity, baseline immutability, labels, determinism."""
import copy
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from backend.app.api.graph import get_graph
from backend.app.api.scenarios import flood_context
from backend.app.core.paths import GPKG, SNAPSHOTS
from backend.app.main import app
from backend.engine.flood import run_flood

pytestmark = pytest.mark.skipif(not GPKG.with_name("drainage.gpkg").exists(), reason="run P02 + P06 pipelines")
client = TestClient(app)


def run(rain, dur=2.0, scale=1.0):
    return run_flood(flood_context(), {"preset": None, "preset_source_id": "syn_rain", "rain_mm_h": rain,
                                       "duration_h": dur, "condition_scale": scale})


def test_rain_below_capacity_no_overloads():
    s = run(1.0)["summary"]
    assert s["drains_overloaded"] == 0 and s["roads_impassable"] == 0 and s["buildings_exposed"] == 0


def test_overloads_monotonic_in_rain():
    counts = [run(r)["summary"]["drains_overloaded"] for r in (5, 10, 15, 20, 40, 80, 120)]
    assert counts == sorted(counts) and counts[-1] > counts[0]
    roads = [run(r)["summary"]["roads_impassable"] for r in (10, 40, 80)]
    assert roads == sorted(roads)


def test_baseline_unchanged_after_run():
    def digest():
        G = get_graph()
        edges = sorted((u, v, k, json.dumps(d, sort_keys=True, default=str)) for u, v, k, d in G.edges(keys=True, data=True))
        return hashlib.sha1(json.dumps([edges, flood_context().drain, flood_context().cat], sort_keys=True,
                                       default=str).encode()).hexdigest()
    before, ctx_before = digest(), copy.deepcopy(flood_context().drain)
    run(80, scale=0.5)
    assert digest() == before and flood_context().drain == ctx_before


def test_labels_and_explanations():
    res = run(80)
    assert res["data_status"] == "modelled (simulated inputs)" and "not a prediction" in res["label"]
    road = next(a for a in res["affected"] if a["kind"] == "road" and a["state"] == "impassable")
    ex = res["explanations"][road["asset_id"]]
    assert ex["path"][0]["from"] == "rain" and any(s["edge"] == "capacity" for s in ex["path"])
    assert any(i["data_status"] == "simulated" for i in ex["inputs"]) and ex["assumptions"] and ex["improve"]
    assert 0 <= ex["risk"]["index"] <= 1 and "not a probability" in ex["risk"]["label"]


def test_deterministic():
    a, b = run(40), run(40)
    a.pop("generated_at"), b.pop("generated_at")
    assert a == b


def test_endpoint_presets_and_validation():
    r = client.post("/api/scenarios/flood", json={"preset": "moderate"}).json()
    assert r["params"]["preset"] == "moderate" and r["summary"]["drains_overloaded"] <= 10  # "few/no" overloads
    assert client.post("/api/scenarios/flood", json={"preset": "nope"}).status_code == 404
    assert client.post("/api/scenarios/flood", json={}).status_code == 422
    custom = client.post("/api/scenarios/flood", json={"preset": "heavy", "rain_mm_h": 41}).json()
    assert custom["params"]["preset"] is None  # overridden values never keep the preset label


@pytest.mark.skipif(not (SNAPSHOTS / "flood_heavy.json").exists(), reason="run scripts/make_snapshots.py")
def test_heavy_matches_snapshot():
    snap = json.loads((SNAPSHOTS / "flood_heavy.json").read_text(encoding="utf-8"))
    live = client.post("/api/scenarios/flood", json={"preset": "heavy"}).json()
    assert live["summary"] == snap["summary"] and live["result_id"] == snap["result_id"]
