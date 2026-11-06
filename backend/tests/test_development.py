"""P09: development assessment — baseline immutability, determinism, verdict rule, insufficient data, upgrades."""
import copy
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from backend.app.api.graph import get_graph
from backend.app.api.scenarios import flood_context
from backend.app.core.paths import GPKG
from backend.app.main import app
from backend.app.services.layer_store import get_store
from backend.engine.development import VERDICTS, suitability_index, verdict

KEY = ["drainage", "flood_exposure", "road_access", "critical_facilities"]
needs = pytest.mark.skipif(not (GPKG.parents[1] / "curated" / "sites.geojson").exists(), reason="run pipelines.make_sites")
client = TestClient(app)


def post(**kw):
    return client.post("/api/development/assess", json={"use": "commercial", "floors": 10, **kw})


@pytest.mark.parametrize("statuses,expected", [
    ({"drainage": "pass", "flood_exposure": "fail", "road_access": "pass"}, VERDICTS["fail"]),
    ({"drainage": "conditional", "flood_exposure": "pass", "road_access": "pass"}, VERDICTS["conditional"]),
    ({"drainage": "fail", "flood_exposure": "conditional"}, VERDICTS["fail"]),  # fail beats conditional
    ({"drainage": "insufficient_data", "flood_exposure": "insufficient_data", "road_access": "pass"}, VERDICTS["insufficient"]),
    ({"drainage": "pass", "flood_exposure": "pass", "road_access": "pass", "critical_facilities": "pass",
      "electrical": "insufficient_data", "water_supply": "insufficient_data"}, VERDICTS["pass"]),  # non-key gaps
])
def test_verdict_rule_table(statuses, expected):
    assert verdict(statuses, KEY) == expected


def test_index_ignores_unassessed_and_never_approves():
    idx = suitability_index({"drainage": "pass", "flood_exposure": "fail", "electrical": "insufficient_data"},
                            {"drainage": 0.5, "flood_exposure": 0.5, "electrical": 0.1})
    assert idx["value"] == 0.5 and "not an approval" in idx["label"]
    assert not any("approved" in v.lower() for v in VERDICTS.values())


@needs
def test_baseline_unchanged_and_deterministic():
    def digest():
        G = get_graph()
        e = sorted((u, v, k) for u, v, k in G.edges(keys=True))
        lay = {k: (len(v.gdf), hashlib.sha1(v.full).hexdigest()) for k, v in get_store().layers.items()}
        return hashlib.sha1(json.dumps([e, lay, flood_context().drain], sort_keys=True, default=str).encode()).hexdigest()
    before, drains = digest(), copy.deepcopy(flood_context().drain)
    a = post(site_id="S2", upgrades=["detention", "drain_upsize"]).json()
    b = post(site_id="S2", upgrades=["drain_upsize", "detention"]).json()
    assert digest() == before and flood_context().drain == drains
    a.pop("label_option"), b.pop("label_option")
    assert a == b  # same inputs (upgrade order irrelevant) → same output


@needs
def test_upgrades_reduce_drainage_load():
    a = {c["dimension"]: c for c in post(site_id="S2").json()["checks"]}["drainage"]
    b = {c["dimension"]: c for c in post(site_id="S2", upgrades=["detention", "drain_upsize"]).json()["checks"]}["drainage"]
    assert b["numbers"]["load_after"] < a["numbers"]["load_after"]
    assert b["numbers"]["added_runoff_m3s"] <= a["numbers"]["added_runoff_m3s"]


@needs
def test_transformer_upgrade_improves_electrical():
    a = {c["dimension"]: c for c in post(site_id="S2").json()["checks"]}["electrical"]
    b = {c["dimension"]: c for c in post(site_id="S2", upgrades=["transformer"]).json()["checks"]}["electrical"]
    assert b["value"] <= 0.8 < a["value"] or b["value"] < a["value"]
    assert b["status"] == "pass" and b["numbers"]["new_rating_kva"] >= 640 * 1.25


@needs
def test_insufficient_data_dimensions_and_demands():
    r = post(site_id="S1").json()
    c = {x["dimension"]: x for x in r["checks"]}
    assert c["water_supply"]["status"] == "insufficient_data" and c["water_supply"]["value"] > 0  # demand still reported
    assert c["electrical"]["status"] in {"pass", "conditional", "fail"} and c["electrical"]["numbers"]["transformer"]
    assert r["label"] == "Screening assessment — not an approval" and r["overlay"]["edges"]


@needs
def test_compare_and_validation():
    body = {"options": [{"site_id": "S2", "label": "A"}, {"site_id": "S2", "upgrades": ["detention", "drain_upsize", "transformer"], "label": "B"},
                        {"site_id": "S1", "label": "C"}]}
    r = client.post("/api/development/compare", json=body).json()
    assert set(r["verdicts"]) == {"A", "B", "C"} and r["what_changed"]["A → B"] and len(r["table"]) == 7
    assert "approved" not in json.dumps(r).lower()
    far = {"type": "Polygon", "coordinates": [[[88.0, 22.0], [88.001, 22.0], [88.001, 22.001], [88.0, 22.001], [88.0, 22.0]]]}
    assert post(geometry=far).status_code == 422
    assert post(site_id="S9").status_code == 404
    assert post().status_code == 422
