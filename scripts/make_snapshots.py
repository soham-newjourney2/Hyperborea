"""P04: freeze API responses into frontend/public/snapshots/ for the offline fallback.

Run with the API up:  python scripts/make_snapshots.py [api_base]   (default http://127.0.0.1:8000/api)
File names must match `snapshotName()` in frontend/src/lib/api.ts. Regenerate at the end of every phase.
"""
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "public" / "snapshots"
# Same extents the map requests (MapView FULL_EXTENT): these two in full, the rest pilot-only.
FULL_EXTENT = {"facilities", "boundary", "drains", "drain_nodes", "outfalls", "catchments", "sites",
               "substations", "transformers", "feeders"}  # must match MapView FULL_EXTENT


def main(base: str = "http://127.0.0.1:8000/api") -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    c = httpx.Client(base_url=base, timeout=60)
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
    # P08 fixed demo results (UI fallback + expected-output test).
    for preset in ("heavy", "extreme"):
        body = c.post("/scenarios/flood", json={"preset": preset}).raise_for_status().content
        files[f"flood_{preset}.json"] = body
        (ROOT / "data" / "snapshots").mkdir(parents=True, exist_ok=True)
        (ROOT / "data" / "snapshots" / f"flood_{preset}.json").write_bytes(body)
    # P09 fixed demo comparison: A = S2 as-is, B = S2 + detention + drain upsize, C = S1 alternative site.
    cmp = {"options": [{"site_id": "S2", "label": "A · S2 as proposed"},
                       {"site_id": "S2", "upgrades": ["detention", "drain_upsize", "transformer"], "label": "B · S2 + upgrades"},
                       {"site_id": "S1", "label": "C · alternative site S1"}]}
    body = c.post("/development/compare", json=cmp).raise_for_status().content
    files["dev_compare.json"] = body
    (ROOT / "data" / "snapshots" / "dev_compare.json").write_bytes(body)
    # Backend's own weather fallback (cache format) → data/snapshots/weather.json
    for name in ("weather.json", "air.json"):  # backend fallbacks (cache format)
        cache = ROOT / "local" / "cache" / name
        if cache.exists():
            (ROOT / "data" / "snapshots").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(cache, ROOT / "data" / "snapshots" / name)

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    files["health.json"] = json.dumps({**health, "status": "snapshot", "snapshot_at": stamp}).encode()
    for old in OUT.glob("*.json"):
        old.unlink()
    for name, body in files.items():
        (OUT / name).write_bytes(body)
    total = sum(len(b) for b in files.values()) / 1e6
    print(f"wrote {len(files)} snapshots ({total:.1f} MB) to {OUT.relative_to(ROOT)} at {stamp}")


if __name__ == "__main__":
    main(*sys.argv[1:])
