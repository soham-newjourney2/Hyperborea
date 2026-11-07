"""P11: DEMO water-quality points (simulated — no published values available, O-04) → data/synthetic/water_quality.geojson.

8 sampling points placed on real OSM canals / water bodies in and around the pilot; pH, turbidity and TDS are
seeded random values in plausible urban-canal ranges, each with unit and a sample date. Points only — never
interpolated. Replace with curated measurements (data/curated/water_quality.geojson) when available.
Run:  python -m pipelines.make_water_demo
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import geopandas as gpd
import numpy as np

from pipelines.osm_common import ROOT
from backend.app.core import regions as R  # noqa: E402  (P16: HYPERBOREA_REGION → paths, CRS, timezone)

UTM = R.metric_crs()
SEED = 7
N = 8
OUT = R.data_dir("synthetic") / "water_quality.geojson"
# Plausible ranges for urban canals / wetland ponds (assumed, demo only).
RANGES = {"ph": (6.6, 8.4, "pH units"), "turbidity": (8.0, 85.0, "NTU"), "tds": (180.0, 950.0, "mg/L")}
REFERENCE = {"ph": "IS 10500 desirable 6.5–8.5 (drinking water; context only)",
             "turbidity": "IS 10500 acceptable ≤ 1 NTU, permissible ≤ 5 NTU (drinking water; context only)",
             "tds": "IS 10500 acceptable ≤ 500 mg/L, permissible ≤ 2000 mg/L (drinking water; context only)"}


def main() -> None:
    rng = np.random.default_rng(SEED)
    g = R.data_dir("processed") / "hyperborea.gpkg"
    bnd = gpd.read_file(g, layer="boundary").to_crs(UTM).geometry.iloc[0]
    ww = gpd.read_file(g, layer="waterways").to_crs(UTM)
    ww = ww[ww.distance(bnd) < 600]
    canals = ww[ww.asset_type == "canal"]
    ponds = ww[ww.asset_type.isin(["water", "wetland"]) & ww.geom_type.str.contains("Polygon")]
    pts, where = [], []
    # spread points along the canals (by length) + a few pond centroids
    for _, r in canals.assign(L=canals.length).sort_values("L", ascending=False).head(3).iterrows():
        line = r.geometry.intersection(bnd.buffer(600))
        for f in (0.25, 0.6):
            if not line.is_empty and line.length > 100:
                pts.append(line.interpolate(f, normalized=True))
                where.append(r["name"] if isinstance(r["name"], str) else "unnamed canal")
    for _, r in ponds.assign(a=ponds.area).sort_values("a", ascending=False).head(N - len(pts)).iterrows():
        pts.append(r.geometry.representative_point())
        where.append(r["name"] if isinstance(r["name"], str) else f"{r.asset_type} body")
    pts, where = pts[:N], where[:N]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    for i, (p, w) in enumerate(zip(pts, where), 1):
        d = date(2026, 10, 1) + timedelta(days=int(rng.integers(0, 30)))
        vals = {k: round(float(rng.uniform(lo, hi)), 1 if k != "tds" else 0) for k, (lo, hi, _) in RANGES.items()}
        rows.append({
            "asset_id": f"wq_syn_{i:02d}", "asset_type": "water_sample_point", "name": f"Demo sample {i:02d} · {w}",
            "data_status": "simulated", "source_id": "syn_water", "observed_at": None, "ingested_at": now,
            "confidence": "low",
            "assumptions": "DEMO DATA: seeded random values in plausible ranges — not a measurement; no interpolation",
            "attrs": json.dumps({"water_body": w, "sample_date": d.isoformat(),
                                 "parameters": [{"parameter": k, "value": vals[k], "unit": RANGES[k][2],
                                                 "reference": REFERENCE[k]} for k in RANGES],
                                 "ph": vals["ph"], "turbidity_ntu": vals["turbidity"], "tds_mg_l": vals["tds"]}),
            "in_pilot": bool(p.within(bnd)),
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(rows, geometry=pts, crs=UTM).to_crs(4326).to_file(OUT, driver="GeoJSON")
    print(f"wrote {len(rows)} demo points →", OUT.relative_to(ROOT), "|", ", ".join(sorted(set(where))))


if __name__ == "__main__":
    main()
