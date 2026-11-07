"""P14: grounding check, deterministic template, health index range, report + explain endpoints."""
import pytest
from fastapi.testclient import TestClient

from backend.app.core.paths import GPKG
from backend.app.main import app
from backend.engine import explain as ex

client = TestClient(app)
needs = pytest.mark.skipif(not GPKG.with_name("drainage.gpkg").exists(), reason="run P06 pipelines")
FACT = {"scenario": {"preset": "heavy", "rain_mm_h": 40, "duration_h": 2, "condition_scale": 1.0},
        "label": "Scenario-based estimate — not a prediction", "data_status": "modelled (simulated inputs)",
        "summary": {"drains_overloaded": 46, "drains_total": 542, "roads_impassable": 32, "road_km_impassable": 2.18}}


def test_grounding_rejects_invented_number():
    ok, bad = ex.grounded("46 of 542 drains overflow and 32 roads (2.18 km) close under 40 mm/h.", FACT)
    assert ok and not bad
    ok, bad = ex.grounded("46 drains overflow and 17 hospitals close.", FACT)
    assert not ok and "17" in bad
    assert ex.grounded("about 2.2 km of road", FACT)[0]  # rounding of 2.18 is allowed
    assert not ex.grounded("about 2.5 km of road", FACT)[0]
    # spelled-out numbers dodge the digit check → rejected; invented quantities with a real number → rejected
    assert not ex.grounded("Forty-one hospitals will be isolated.", FACT)[0]
    assert not ex.grounded("an average temperature drop of 2.18 degrees Celsius", FACT)[0]
    assert ex.grounded("one access road is blocked", FACT)[0]  # small words are fine


def test_template_is_deterministic_and_grounded():
    a, b = ex.template(FACT), ex.template(FACT)
    assert a == b and "not a prediction" in a and ex.grounded(a, FACT)[0]


@needs
def test_health_index_range_and_reasons():
    for t in ("drain", "transformer", "road"):
        r = client.get("/api/infra-health", params={"type": t, "top": 200}).json()
        assert r["items"] and all(0 <= i["health_index"] <= 100 for i in r["items"])
        idx = [i["health_index"] for i in r["items"]]
        assert idx == sorted(idx) and r["items"][0]["reasons"] and "age" in r["simulated_inputs"]


@needs
def test_report_and_explain_endpoints():
    res = client.post("/api/scenarios/flood", json={"preset": "extreme"}).json()
    rep = client.get(f"/api/report/{res['result_id']}")
    assert rep.status_code == 200 and rep.json()["attributions"] and rep.json()["affected"]
    aid = res["affected"][0]["asset_id"]
    e = client.post("/api/explain", json={"result_id": res["result_id"], "asset_id": aid, "mode": "template"}).json()
    assert e["mode"] == "template" and e["grounded"] and aid in e["text"]
    assert client.get("/api/report/nope").status_code == 404
    st = client.get("/api/explain/status").json()
    assert "llm" in st and st["default_mode"] in ("template", "ollama", "llm")
