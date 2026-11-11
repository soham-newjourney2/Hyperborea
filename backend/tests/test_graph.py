"""P07: relationship engine — registry, rules, isolation, DAG consistency, endpoints."""
import json

import geopandas as gpd
import networkx as nx
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString, Polygon

from backend.app.api.graph import get_graph
from backend.app.core.paths import GPKG
from backend.app.main import app
from backend.engine import graph as eg
from backend.engine.relationships import EDGE_TYPES

needs_data = pytest.mark.skipif(not GPKG.with_name("drainage.gpkg").exists(), reason="run P02 + P06 pipelines")


def _frame(rows, geoms):
    base = {"name": None, "data_status": "observed", "source_id": "osm", "attrs": "{}"}
    return gpd.GeoDataFrame([{**base, **r} for r in rows], geometry=geoms, crs=4326)


def test_isolated_asset_gets_no_physical_edge():
    # road along the equator near lon 88.43; one building next to it, one ~1 km away (VISION §19.3)
    roads = _frame([{"asset_id": "rd_1", "asset_type": "road"}], [LineString([(88.430, 22.57), (88.432, 22.57)])])
    near = Polygon([(88.4310, 22.57015), (88.4311, 22.57015), (88.4311, 22.57025), (88.4310, 22.57025)])
    far = Polygon([(88.4400, 22.5800), (88.4401, 22.5800), (88.4401, 22.5801), (88.4400, 22.5801)])
    blds = _frame([{"asset_id": "b_near", "asset_type": "building"}, {"asset_id": "b_far", "asset_type": "building"}],
                  [near, far])
    G = eg.build_graph({"roads": roads, "buildings": blds})
    assert G.has_edge("b_near", "rd_1", key="ACCESSIBLE_VIA")
    assert G.degree("b_far") == 0  # no road within 50 m → no fabricated edge


def test_unknown_edge_type_rejected():
    G = nx.MultiDiGraph()
    G.add_nodes_from(["a", "b"])
    with pytest.raises(KeyError):
        eg.add_edge(G, "MADE_UP", "a", "b", rule="x", data_status="simulated", confidence="low")


@pytest.fixture(scope="module")
def G():
    return get_graph()


@needs_data
def test_graph_types_and_rules(G):
    kinds = {d["kind"] for _, d in G.nodes(data=True)}
    assert len(kinds) >= 3 and {"building", "road", "drain", "facility", "catchment"} <= kinds
    etypes = {k for _, _, k in G.edges(keys=True)}
    assert etypes <= set(EDGE_TYPES) and len(etypes) >= 5
    for _, _, d in G.edges(data=True):
        assert d["rule"] and d["relationship_id"] and d["data_status"] and d["confidence"]


@needs_data
def test_upstream_is_ancestors_on_dag(G):
    drains = gpd.read_file(GPKG.with_name("drainage.gpkg"), layer="drains")
    down = {a: json.loads(s)["drains_to"] for a, s in zip(drains.asset_id, drains["attrs"])}
    T = nx.DiGraph(list(down.items()))
    busiest = max(down, key=lambda s: len(nx.ancestors(T, s)))
    assert eg.upstream(G, busiest) <= nx.ancestors(T, busiest)
    assert eg.upstream(G, busiest) == nx.ancestors(T, busiest)
    assert eg.downstream(G, busiest)[-1].startswith("out_cur_")


@needs_data
def test_endpoints():
    c = TestClient(app)
    s = c.get("/api/graph/summary").json()
    assert s["edges"] > 0 and len(s["node_kinds"]) >= 4 and len(s["edge_types"]) >= 5
    fac = next(n for n, d in get_graph().nodes(data=True) if d["kind"] == "facility" and get_graph().out_degree(n))
    nb = c.get(f"/api/graph/neighbors/{fac}", params={"depth": 2}).json()
    assert nb["center"] == fac and any(e["type"] == "DEPENDS_ON" for e in nb["edges"])
    ids = {n["id"] for n in nb["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in nb["edges"])
    rel = c.get(f"/api/assets/{fac}").json()["relationships"]
    assert rel and all(r["rule"] for r in rel)
    assert c.get("/api/graph/neighbors/nope").status_code == 404
    road = next(e["target"] for e in nb["edges"] if e["type"] == "DEPENDS_ON")
    p = c.get("/api/graph/path", params={"src": fac, "dst": road}).json()
    assert p["hops"] == 1
