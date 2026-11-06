"""P06: simulated drainage network — DAG, reachability, Manning, provenance, catchment coverage."""
import json

import geopandas as gpd
import networkx as nx
import pyogrio
import pytest

from backend.app.core.paths import GPKG
from backend.engine.hydraulics import manning_full_circular, rational_runoff

DRN = GPKG.with_name("drainage.gpkg")
HAS = DRN.exists() and "drains" in {n for n, _ in pyogrio.list_layers(DRN)}
needs_data = pytest.mark.skipif(not HAS, reason="run pipelines.build_drainage first")


def test_manning_hand_case():
    # d = 0.6 m, S = 0.002, n = 0.015: A = 0.28274 m², R = 0.15 m, R^(2/3) = 0.28231, √S = 0.044721
    # Q = 66.667 × 0.28274 × 0.28231 × 0.044721 = 0.23798 m³/s
    assert manning_full_circular(0.6, 0.002) == pytest.approx(0.23798, rel=1e-3)
    ratio = manning_full_circular(1.2, 0.002) / manning_full_circular(0.6, 0.002)
    assert ratio == pytest.approx(2 ** (8 / 3), rel=1e-9)  # Q ∝ d^(8/3)
    with pytest.raises(ValueError):
        manning_full_circular(0.6, 0)


def test_rational_runoff_hand_case():
    # C 0.9, 40 mm/h, 1 ha → 0.9 × 40 × 10 000 / 3.6e6 = 0.1 m³/s
    assert rational_runoff(0.9, 40, 10_000) == pytest.approx(0.1)


@pytest.fixture(scope="module")
def net():
    d = gpd.read_file(DRN, layer="drains")
    o = gpd.read_file(DRN, layer="outfalls")
    return d, d["attrs"].map(json.loads), o


@needs_data
def test_drains_form_dag_and_reach_outfall(net):
    d, a, o = net
    down = dict(zip(d.asset_id, a.map(lambda x: x["drains_to"])))
    g = nx.DiGraph(list(down.items()))
    assert nx.is_directed_acyclic_graph(g)
    outfalls = set(o.asset_id)
    for sid in down:
        cur, hops = sid, 0
        while cur not in outfalls:
            cur, hops = down[cur], hops + 1
            assert hops < len(down), f"{sid} never reaches an outfall"


@needs_data
def test_capacity_matches_formula(net):
    d, a, _ = net
    for x in a:
        q = manning_full_circular(x["diameter_m"], x["slope"], x["manning_n"])
        assert x["capacity_m3s"] == pytest.approx(q, abs=1e-3)
        assert x["effective_capacity_m3s"] == pytest.approx(q * x["condition_factor"], abs=2e-3)
        assert 0.6 <= x["condition_factor"] <= 1.0 and x["slope"] >= 0.002


@needs_data
def test_drainage_provenance(net):
    d, _, o = net
    assert set(d.data_status) <= {"simulated", "curated"} and set(d.source_id) == {"syn_drain"}
    assert set(o.data_status) == {"curated"} and set(o.source_id) == {"cur_outfall"}
    assert d.assumptions.str.len().min() > 50  # every drain names its rules


@needs_data
def test_catchments_cover_boundary():
    c = gpd.read_file(DRN, layer="catchments").to_crs(32645)
    b = gpd.read_file(GPKG, layer="boundary").to_crs(32645).area.iloc[0]
    assert c.area.sum() == pytest.approx(b, rel=0.02)
    cs = c["attrs"].map(lambda s: json.loads(s)["runoff_c"])
    assert cs.between(0.40, 0.90).all()
