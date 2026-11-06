"""P06: drainage preview PNG → presentation/screens/P06_drainage_preview.png (outfall check for the user)."""
import json

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from pipelines.osm_common import ROOT  # noqa: E402

GPKG = ROOT / "data" / "processed" / "hyperborea.gpkg"


def main() -> None:
    DRN = GPKG.with_name("drainage.gpkg")
    L = {n: gpd.read_file(DRN if n in ("drains", "outfalls", "catchments") else GPKG, layer=n).to_crs(32645)
         for n in ["boundary", "drains", "outfalls", "waterways", "catchments", "buildings"]}
    d, o, b = L["drains"], L["outfalls"], L["boundary"]
    a = d["attrs"].map(json.loads)
    cap = a.map(lambda x: x["effective_capacity_m3s"])
    fig, ax = plt.subplots(figsize=(11, 10))
    L["catchments"].boundary.plot(ax=ax, color="#cbd5e1", lw=0.3)
    w = L["waterways"]
    w[w.geom_type.str.contains("Polygon")].plot(ax=ax, color="#bfdbfe", lw=0)
    w[w.asset_type == "canal"].plot(ax=ax, color="#2563eb", lw=2)
    L["buildings"].plot(ax=ax, color="#e5e7eb", lw=0)
    d.plot(ax=ax, column=cap, cmap="Blues", vmin=0, vmax=float(np.quantile(cap, 0.95)),
           linewidth=0.6 + 2.4 * a.map(lambda x: x["diameter_m"]) / 1.2, legend=True,
           legend_kwds={"label": "effective capacity (m³/s, simulated)", "shrink": 0.6})
    # flow arrows at segment midpoints (upstream → downstream)
    for g in d.geometry:
        if g.length < 40:
            continue
        p0, p1 = g.interpolate(0.45, normalized=True), g.interpolate(0.55, normalized=True)
        ax.annotate("", xy=(p1.x, p1.y), xytext=(p0.x, p0.y),
                    arrowprops={"arrowstyle": "-|>", "color": "#0f172a", "lw": 0.6, "mutation_scale": 7})
    oa = o["attrs"].map(json.loads)
    for g, aid, at in zip(o.geometry, o["asset_id"], oa):
        col = "#16a34a" if at["snapped"] else "#dc2626"
        ax.plot(g.x, g.y, marker="*", ms=18, color=col, mec="k", mew=0.6, zorder=5)
        ax.annotate(f"{aid[-2:]}  {at['receiving_water'] or 'unnamed ' + at.get('receiving_kind', 'canal')} ({at['distance_to_water_m']:.0f} m)"
                    f"\n{at['n_upstream_segments']} drains" + ("" if at["snapped"] else " — NO CANAL NEARBY"),
                    (g.x, g.y), xytext=(8, 8), textcoords="offset points", fontsize=8,
                    bbox={"boxstyle": "round", "fc": "white", "ec": col, "alpha": 0.9})
    b.boundary.plot(ax=ax, color="#d7191c", lw=2)
    x0, y0, x1, y1 = b.buffer(300).total_bounds
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_axis_off()
    ax.set_title("Hyperborea P06 — SIMULATED drainage network, Sector V (not municipal records)\n"
                 f"{len(d)} drains · {len(o)} outfalls (★ green = ≤ 80 m from canal, red = none nearby) · "
                 "arrows = flow direction\n© OpenStreetMap contributors · Copernicus DEM GLO-30", fontsize=10)
    out = ROOT / "presentation" / "screens" / "P06_drainage_preview.png"
    fig.savefig(out, dpi=110, bbox_inches="tight")
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
