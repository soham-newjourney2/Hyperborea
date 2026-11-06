"""P10: simulated electrical network — supply topology, loading maths, cascade hop, baseline immutability."""
import copy
import json
from collections import Counter

import geopandas as gpd
import pytest

from backend.app.api.graph import get_graph
from backend.app.api.scenarios import flood_context
from backend.app.core.paths import GPKG
from backend.engine.flood import run_flood
from backend.engine.relationships import EDGE_TYPES

PWR = GPKG.with_name("power.gpkg")
pytestmark = pytest.mark.skipif(not PWR.exists(), reason="run pipelines.build_power")


@pytest.fixture(scope="module")
def trf():
    t = gpd.read_file(PWR, layer="transformers")
    return t, t["attrs"].map(json.loads)


def test_every_building_supplied_by_exactly_one_transformer(trf):
    _, a = trf
    supplied = Counter(b for x in a for b in x["buildings"])
    blds = set(gpd.read_file(GPKG, layer="buildings").asset_id)
    assert set(supplied) == blds and max(supplied.values()) == 1
    G = get_graph()
    for b in list(blds)[:200]:
        sup = [u for u, _, k in G.in_edges(b, keys=True) if k == "SUPPLIES"]
        assert len(sup) == 1 and G.nodes[sup[0]]["kind"] == "transformer"


def test_loading_maths_and_ratings(trf):
    t, a = trf
    for x in a:
        assert x["rating_kva"] == x["unit_kva"] * x["units"]
        assert x["loading_pct"] == pytest.approx(100 * x["load_kva"] / x["rating_kva"], abs=0.1)
        assert x["rating_kva"] >= 1.25 * x["load_kva"] - 1e-6  # 25 % margin
        assert x["plinth_m"] == 0.6
    assert set(t.data_status) == {"simulated"} and EDGE_TYPES["SUPPLIES"]["active"]


def _run(rain, plinth=None):
    ctx = flood_context()
    if plinth is not None:  # scenario copy only — never the cached baseline
        ctx = copy.copy(ctx)
        ctx.trf = {k: {**v, "plinth_m": plinth} for k, v in ctx.trf.items()}
    return run_flood(ctx, {"preset": None, "preset_source_id": "syn_rain", "rain_mm_h": rain, "duration_h": 2,
                           "condition_scale": 1.0})


def test_electrical_hop_only_when_depth_at_or_above_plinth():
    r = _run(80)
    for tid, t in r["layers"]["transformers"].items():
        assert t["depth_m"] >= flood_context().trf[tid]["plinth_m"]
        assert r["explanations"][tid]["path"][-1]["edge"] == "LOCATED_WITHIN"
    # plinth above the 1 m ponding cap → no shutdowns, no power loss anywhere
    hi = _run(80, plinth=1.5)
    assert hi["summary"]["transformers_shutdown"] == 0 and hi["summary"]["buildings_power_loss"] == 0
    assert all(f["power"] != "loss" for f in hi["layers"]["facilities"].values())
    assert _run(1)["summary"]["transformers_shutdown"] == 0


def test_power_loss_chain_and_baseline_untouched():
    before = copy.deepcopy(flood_context().trf)
    r = _run(80)
    assert flood_context().trf == before
    lost = [a for a in r["affected"] if a["state"] == "power_loss"]
    for a in lost:
        ex = r["explanations"][a["asset_id"]]
        assert ex["path"][-1]["values"]["backup_power"] == "unknown"
        assert any(s["edge"] == "LOCATED_WITHIN" and s["to"].startswith("trf_syn_") for s in ex["path"])
    assert r["summary"]["buildings_power_loss"] == len(r["layers"]["buildings_power"])
