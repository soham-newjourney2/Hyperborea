"""P02 step 6: quick preview PNG of the GeoPackage → presentation/screens/P02_preview.png"""
import json

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from pipelines.osm_common import ROOT  # noqa: E402

GPKG = ROOT / "data" / "processed" / "hyperborea.gpkg"
HCOL = {"observed": "#1b7837", "modelled": "#f1a340", "assumed": "#9e9ac8"}


def main() -> None:
    L = {n: gpd.read_file(GPKG, layer=n).to_crs(32645) for n in
         ["boundary", "buildings", "roads", "facilities", "waterways"]}
    bnd = L["boundary"]
    x0, y0, x1, y1 = bnd.buffer(600).total_bounds
    fig, ax = plt.subplots(figsize=(10, 10))
    w = L["waterways"]
    w[w.geom_type.str.contains("Polygon")].plot(ax=ax, color="#a6cee3", lw=0)
    w[w.geom_type.str.contains("Line")].plot(ax=ax, color="#1f78b4", lw=1.2)
    L["roads"].plot(ax=ax, color="#888", lw=0.5)
    b = L["buildings"]
    b[~b.in_pilot.astype(bool)].plot(ax=ax, color="#ddd", lw=0)
    bp = b[b.in_pilot.astype(bool)]
    hs = bp["attrs"].map(lambda a: json.loads(a)["height_status"])
    for s, c in HCOL.items():
        if (hs == s).any():
            bp[hs == s].plot(ax=ax, color=c, lw=0, label=f"building height {s} ({int((hs == s).sum())})")
    f = L["facilities"]
    for t, m in {"hospital": "P", "clinic": "+", "school": "s", "college": "^", "university": "^",
                 "fire_station": "*", "police": "D", "metro_station": "o", "rail_station": "o"}.items():
        ft = f[f.asset_type == t]
        if len(ft):
            ft.plot(ax=ax, marker=m, markersize=60, color="#d7191c", edgecolor="k", lw=0.4, label=f"{t} ({len(ft)})")
    bnd.boundary.plot(ax=ax, color="#d7191c", lw=2.5)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_axis_off()
    ax.legend(loc="lower left", fontsize=8, framealpha=0.9)
    ax.set_title(f"Hyperborea P02 — {bnd['name'].iloc[0]} pilot: {len(bp)} buildings, "
                 f"{int(L['roads'].in_pilot.astype(bool).sum())} road edges\n© OpenStreetMap contributors (ODbL)",
                 fontsize=10)
    out = ROOT / "presentation" / "screens" / "P02_preview.png"
    fig.savefig(out, dpi=110, bbox_inches="tight")
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
