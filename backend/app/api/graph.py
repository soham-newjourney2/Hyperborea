"""P07 endpoints: /graph/summary, /graph/neighbors/{id}, /graph/path (planning §8)."""
import networkx as nx
from fastapi import APIRouter, HTTPException, Query

from ...engine import graph as eg
from ..core.regions import per_region
from ..services.layer_store import get_store

router = APIRouter()


@per_region
def get_graph() -> nx.MultiDiGraph:
    return eg.build_graph({k: v.gdf for k, v in get_store().layers.items()})


@router.get("/graph/summary")
def graph_summary() -> dict:
    return eg.summary(get_graph())


@router.get("/graph/neighbors/{asset_id}")
def graph_neighbors(asset_id: str, depth: int = Query(1, ge=1, le=3), types: str | None = None,
                    max_nodes: int = Query(250, ge=10, le=600)) -> dict:
    tset = {t.strip() for t in types.split(",") if t.strip()} if types else None
    try:
        return eg.neighbors(get_graph(), asset_id, depth=depth, types=tset, max_nodes=max_nodes)
    except KeyError as e:
        raise HTTPException(404, f"Unknown asset {asset_id!r}") from e


@router.get("/graph/path")
def graph_path(src: str, dst: str) -> dict:
    G = get_graph()
    for n in (src, dst):
        if n not in G:
            raise HTTPException(404, f"Unknown asset {n!r}")
    try:
        return eg.path(G, src, dst)
    except nx.NetworkXNoPath as e:
        raise HTTPException(404, f"No relationship path between {src} and {dst}") from e


@router.get("/graph/trace/{drain_id}")
def graph_trace(drain_id: str) -> dict:
    """Upstream set + downstream flow path of a drain (used by the explorer and P08)."""
    G = get_graph()
    if G.nodes.get(drain_id, {}).get("kind") != "drain":
        raise HTTPException(404, f"{drain_id!r} is not a drain")
    return {"drain": drain_id, "upstream": sorted(eg.upstream(G, drain_id)), "downstream": eg.downstream(G, drain_id)}
