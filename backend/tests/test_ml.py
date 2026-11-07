"""P13: surrogate loads + predicts fast, metrics exist, CV layer complete, no torch in the backend runtime."""
import json
import pathlib
import subprocess
import sys
import time

import geopandas as gpd
import pytest
from fastapi.testclient import TestClient

from backend.app.api.scenarios import flood_context
from backend.app.core.paths import PROCESSED, ROOT
from backend.app.main import app
from backend.engine import surrogate as sg

client = TestClient(app)
needs_model = pytest.mark.skipif(not sg.MODEL.exists(), reason="run pipelines.train_surrogate")


@needs_model
def test_surrogate_predicts_all_drains_under_200ms():
    ctx = flood_context()
    sg.quickscan(ctx, 40, 2, 1.0)  # warm (static features cached)
    t0 = time.perf_counter()
    out = sg.quickscan(ctx, 80, 2, 0.8)
    assert (time.perf_counter() - t0) < 0.2
    assert len(out["probabilities"]) == len(ctx.drain) and all(0 <= p <= 1 for p in out["probabilities"].values())
    assert "not validated on real events" in out["label"]


@needs_model
def test_metrics_and_cards():
    m = json.loads(sg.METRICS.read_text(encoding="utf-8"))
    for k in ("precision", "recall", "f1", "roc_auc"):
        assert 0 <= m["surrogate"][k] <= 1 and 0 <= m["baseline"][k] <= 1
    assert m["surrogate"]["f1"] > m["baseline"]["f1"] and "spatial blocks" in m["training"]["split"]
    assert sg.MODEL.stat().st_size < 5 * 1024 * 1024
    cards = {c["id"]: c for c in client.get("/api/models").json()}
    assert cards["ml_surrogate"]["card_markdown"] and "not ML" in cards["cv_water"]["title"]


@needs_model
def test_quickscan_endpoint_matches_engine_broadly():
    r = client.get("/api/ml/quickscan", params={"rain_mm_h": 80, "duration_h": 2, "compare": True}).json()
    assert r["vs_engine"]["agreement_pct"] >= 90 and r["inference_ms"] < 200


@pytest.mark.skipif(not (PROCESSED / "cv_water.gpkg").exists(), reason="run pipelines.cv_water")
def test_cv_layer_props_complete():
    g = gpd.read_file(PROCESSED / "cv_water.gpkg", layer="cv_water")
    assert len(g) and set(g.data_status) == {"modelled"} and set(g.source_id) == {"cv_water"}
    assert g.assumptions.str.contains("not ML").all()
    a = g["attrs"].map(json.loads)
    assert a.map(lambda x: x["method"] == "ndwi_mcfeeters" and x["area_m2"] >= 400 and x["scenes"]).all()


def test_no_torch_in_backend_runtime():
    code = ("import sys; from fastapi.testclient import TestClient; from backend.app.main import app; "
            "c = TestClient(app); c.get('/api/health'); c.get('/api/models'); print('torch' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert out.stdout.strip().endswith("False"), out.stderr[-500:]
    src = "\n".join(p.read_text(encoding="utf-8") for p in pathlib.Path(ROOT / "backend").rglob("*.py")
                    if "tests" not in p.parts)  # this test file itself mentions the strings
    assert "import torch" not in src and "from torch" not in src
