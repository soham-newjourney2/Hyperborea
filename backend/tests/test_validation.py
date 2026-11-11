"""P22 validation: scoring maths, threshold-free AUC, endpoint per region."""
import pytest
from fastapi.testclient import TestClient

from backend.app.core import regions as R
from backend.app.main import app
from backend.engine.validation import auc, scores, worst

client = TestClient(app)


def test_scores_pod_far_csi():
    s = scores(obs={"a", "b", "c"}, pred={"b", "c", "d"}, universe={"a", "b", "c", "d", "e"})
    assert (s["tp"], s["fp"], s["fn"], s["tn"]) == (2, 1, 1, 1)
    assert s["pod"] == round(2 / 3, 3) and s["far"] == round(1 / 3, 3) and s["csi"] == 0.5


def test_auc_random_vs_perfect_and_worst_window():
    obs = {"a", "b"}
    assert auc(obs, {"a": 2, "b": 3, "c": 0, "d": 1}) == 1.0
    assert auc(obs, {"a": 0, "b": 0, "c": 0, "d": 0}) == 0.5  # all ties = no skill
    assert worst([0, 1, 5, 4, 0], 2) == (2, 9)


@pytest.mark.skipif(not (R.data_dir("processed", "chennai_velachery") / "validation.json").exists(),
                    reason="run pipelines.validate_flood for chennai_velachery")
def test_endpoint_chennai_and_absent_region():
    v = client.get("/api/validation", params={"region": "chennai_velachery"}).json()
    assert v["observed"]["catchments_compared"] > 100 and set(v["runs"]) >= {"A_era5", "C_station_era5_timing"}
    assert v["observed"]["urban_brightening_share_post"] > v["observed"]["urban_brightening_share_control"]
    assert client.get("/api/validation", params={"region": "london_stratford"}).status_code == 404
