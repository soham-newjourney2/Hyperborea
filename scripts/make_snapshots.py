"""P04: freeze API responses into frontend/public/snapshots/ for the offline fallback.

Run with the API up:  python scripts/make_snapshots.py [api_base]   (default http://127.0.0.1:8000/api)
Region from HYPERBOREA_REGION (default sector_v) → frontend/public/snapshots/regions/<id>/ (+ snapshots/regions.json).
File names must match `snapshotName()` in frontend/src/lib/api.ts. Regenerate at the end of every phase.
"""
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.core import regions as R  # noqa: E402
from backend.app.core.config import get_settings  # noqa: E402  (admin password from .env)
SNAP_ROOT = ROOT / "frontend" / "public" / "snapshots"
RID = R.current()
OUT = SNAP_ROOT / "regions" / RID
DATA_SNAP = R.data_dir("snapshots")
# Same extents the map requests (MapView FULL_EXTENT): these two in full, the rest pilot-only.
FULL_EXTENT = {"facilities", "boundary", "drains", "drain_nodes", "outfalls", "catchments", "sites",
               "substations", "transformers", "feeders", "water_quality", "cv_water", "sar_flood"}  # must match MapView FULL_EXTENT


def main(base: str = "http://127.0.0.1:8000/api") -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    c = httpx.Client(base_url=base, timeout=60, params={"region": RID})
    if c.get("/health").json().get("auth_required"):  # P20: log in only when the API asks for it
        tok = c.post("/auth/login", json={"password": get_settings().admin_password}).raise_for_status().json()["access_token"]
        c.headers["Authorization"] = f"Bearer {tok}"
    files: dict[str, bytes] = {}

    health = c.get("/health").raise_for_status().json()
    files["region.json"] = c.get("/region").raise_for_status().content
    layers = c.get("/layers").raise_for_status()
    files["layers.json"] = layers.content
    for meta in layers.json():
        lid = meta["id"]
        pilot = lid not in FULL_EXTENT
        r = c.get(f"/layers/{lid}", params={"in_pilot": "true"} if pilot else None).raise_for_status()
        files[f"layer_{lid}{'_pilot' if pilot else ''}.json"] = r.content

    for path in ("weather/current", "weather/forecast", "climate/summary", "scenarios/presets",
                 "environment/air", "environment/water", "environment/landcover", "access/summary"):
        files[path.replace("/", "_") + ".json"] = c.get(f"/{path}").raise_for_status().content
    files["warning.json"] = c.get("/warning").raise_for_status().content  # P21 early-warning outlook
    v = c.get("/validation")  # P22: only regions with a scored event
    if v.status_code == 200:
        files["validation.json"] = v.content
    for t in ("drain", "transformer", "road"):  # P15: health card works offline (top-10 as the UI asks)
        files[f"infra_health_{t}.json"] = c.get("/infra-health", params={"type": t, "top": 10}).raise_for_status().content
    # P08 fixed demo results (UI fallback + expected-output test).
    for preset in ("heavy", "extreme"):
        body = c.post("/scenarios/flood", json={"preset": preset}).raise_for_status().content
        files[f"flood_{preset}.json"] = body
        DATA_SNAP.mkdir(parents=True, exist_ok=True)
        (DATA_SNAP / f"flood_{preset}.json").write_bytes(body)
    # P09 fixed demo comparison: A = S2 as-is, B = S2 + detention + drain upsize, C = S1 alternative site.
    cmp = {"options": [{"site_id": "S2", "label": "A · S2 as proposed"},
                       {"site_id": "S2", "upgrades": ["detention", "drain_upsize", "transformer"], "label": "B · S2 + upgrades"},
                       {"site_id": "S1", "label": "C · alternative site S1"}]}
    body = c.post("/development/compare", json=cmp).raise_for_status().content
    files["dev_compare.json"] = body
    (DATA_SNAP / "dev_compare.json").write_bytes(body)
    # Backend's own weather fallback (cache format) → data/snapshots/weather.json
    for name in ("weather.json", "air.json"):  # backend fallbacks (cache format)
        cache = R.local_dir("cache") / name
        if cache.exists():
            DATA_SNAP.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(cache, DATA_SNAP / name)

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    files["health.json"] = json.dumps({**health, "status": "snapshot", "snapshot_at": stamp}).encode()
    # Region list for the offline switcher: only regions that have snapshots are "ready" offline.
    reg = c.get("/regions").raise_for_status().json()
    have = {RID} | {p.name for p in (SNAP_ROOT / "regions").glob("*") if (p / "health.json").exists()}
    for r in reg["regions"]:
        r["status"] = "ready" if r["id"] in have else "no-data"
    SNAP_ROOT.mkdir(parents=True, exist_ok=True)
    (SNAP_ROOT / "regions.json").write_text(json.dumps(reg), encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        if old.name != "regions.json":
            old.unlink()
    for name, body in files.items():
        (OUT / name).write_bytes(body)
    total = sum(len(b) for b in files.values()) / 1e6
    print(f"{RID}: wrote {len(files)} snapshots ({total:.1f} MB) to {OUT.relative_to(ROOT)} at {stamp}")


if __name__ == "__main__":
    main(*sys.argv[1:])
