"""P12 endpoint: /access/summary?result_id= (planning §8) — baseline or flood-scenario accessibility."""
from collections import OrderedDict

from fastapi import APIRouter, HTTPException

from ...engine import access as ea
from ..core.regions import current, data_dir, per_region

router = APIRouter()
_scen: OrderedDict[str, dict] = OrderedDict()  # result_id → access scenario (LRU 16)


@per_region
def get_access() -> ea.AccessContext | None:
    p = data_dir() / "drive_graph.json"
    return ea.load_context(p) if p.exists() else None


def scenario_for(result: dict) -> dict | None:
    ctx = get_access()
    if ctx is None:
        return None
    rid = f"{current()}:{result['result_id']}"
    if rid not in _scen:
        _scen[rid] = ea.scenario(ctx, result)
        if len(_scen) > 16:
            _scen.popitem(last=False)
    return _scen[rid]


def _minutes(per: dict) -> dict:
    return {b: v["min"] for b, v in per.items()}


@router.get("/access/summary")
def access_summary(result_id: str | None = None) -> dict:
    ctx = get_access()
    if ctx is None:
        raise HTTPException(503, "Drive graph missing — run pipelines.build_access")
    out = {"label": ea.LABEL, "data_status": "modelled", "source_id": "osm", "result_id": result_id, "categories": {}}
    if result_id is None:
        for cat, v in ctx.baseline.items():
            out["categories"][cat] = {"stats": ea.stats(v["buildings"]), "minutes": _minutes(v["buildings"])}
        return out
    from .scenarios import result_cache  # flood results cached by params hash
    res = result_cache().data.get(result_id)
    if res is None:
        raise HTTPException(404, "Unknown result_id — run POST /scenarios/flood first")
    sc = scenario_for(res)
    for cat, v in sc["scenario"].items():
        base = ctx.baseline[cat]["buildings"]
        out["categories"][cat] = {
            **sc["categories"][cat], "minutes": _minutes(v["buildings"]),
            "delta": {b: (None if v["buildings"][b]["min"] is None or base[b]["min"] is None
                          else round(v["buildings"][b]["min"] - base[b]["min"], 2)) for b in base},
        }
    out["removed_roads"], out["slowed_roads"] = sc["removed_roads"], sc["slowed_roads"]
    out["facilities_no_hospital_route"] = sc["facilities_no_hospital_route"]
    return out
