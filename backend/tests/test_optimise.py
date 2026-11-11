"""P23 optimiser: overlays work, budget respected, risk never increases, baseline untouched."""
import pytest
import yaml
from fastapi.testclient import TestClient

from backend.app.core.paths import CONFIG, GPKG
from backend.app.main import app

pytestmark = pytest.mark.skipif(not GPKG.with_name("drainage.gpkg").exists(), reason="run P06 pipelines")


@pytest.fixture(scope="module")
def ctx_params():
    from backend.app.api.scenarios import FloodRequest, flood_context, resolve
    return flood_context(), resolve(FloodRequest(preset="extreme"))


def test_plinth_and_storage_overlays(ctx_params):
    from backend.engine.flood import run_flood
    ctx, p = ctx_params
    base = run_flood(ctx, p)
    t = next(k for k, v in base["layers"]["transformers"].items() if v["state"] == "shutdown")
    raised = run_flood(ctx, p, {"plinth": {t: 1.2}})
    assert t not in raised["layers"]["transformers"] and raised["summary"]["transformers_shutdown"] == base["summary"]["transformers_shutdown"] - 1
    c, v = max(base["layers"]["catchments"].items(), key=lambda kv: kv[1]["overflow_m3"])
    stored = run_flood(ctx, p, {"storage_m3": {c: v["overflow_m3"] + 1}})
    assert c not in stored["layers"]["catchments"]
    assert run_flood(ctx, p)["summary"] == base["summary"]  # baseline never mutated


def test_optimise_respects_budget_and_reduces_risk(ctx_params):
    from backend.engine.optimise import optimise
    ctx, p = ctx_params
    cfg = yaml.safe_load((CONFIG / "costs.yaml").read_text(encoding="utf-8"))
    cur = cfg["currencies"]["INR"]
    out = optimise(ctx, p, 5_000_000, cfg, cur)
    assert out["spent"] <= 5_000_000 and out["plan"]
    assert out["objective_after"] < out["objective_before"]
    objs = [s["objective"] for s in out["curve"]]
    assert all(b <= a for a, b in zip(objs, objs[1:]))  # every accepted step helps
    assert out["plan"][0]["cumulative_cost"] == out["plan"][0]["cost"]


def test_endpoint_currency_per_region():
    c = TestClient(app)
    assert c.get("/api/optimise/config").json()["currency"] == "INR"
    assert c.get("/api/optimise/config", params={"region": "london_stratford"}).json()["symbol"] == "£"
    r = c.post("/api/optimise", json={"preset": "heavy", "budget": 3_000_000}).json()
    assert r["symbol"] == "₹" and "after_result" not in r and r["spent"] <= 3_000_000
