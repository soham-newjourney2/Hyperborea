"""In-memory layer store: GeoPackage → GeoDataFrames + pre-serialised GeoJSON (P03)."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import geopandas as gpd
import numpy as np
import pyogrio
import shapely

from ..core.paths import GPKG

# id → (title, group, default visible). Order = Layer Manager order.
LAYER_META: dict[str, tuple[str, str, bool]] = {
    "boundary": ("Pilot boundary", "Context", True),
    "buildings": ("Buildings", "Built environment", True),
    "roads": ("Roads", "Mobility", True),
    "facilities": ("Critical facilities", "Critical facilities", True),
    "waterways": ("Waterways & water bodies", "Water", False),
    "water_quality": ("Water quality points", "Water", False),
    "cv_water": ("Surface water (NDWI index, not ML)", "Water", False),
    "drains": ("Drains (simulated)", "Drainage", False),
    "outfalls": ("Outfalls", "Drainage", False),
    "catchments": ("Catchments (simulated)", "Drainage", False),
    "drain_nodes": ("Manholes (simulated)", "Drainage", False),
    "landuse": ("Land use", "Land", False),
    "sites": ("Candidate sites", "Development", False),
    "substations": ("Substations (OSM, curated)", "Energy", False),
    "transformers": ("Transformers (simulated)", "Energy", False),
    "feeders": ("11 kV feeders (schematic)", "Energy", False),
    "osm_power": ("Power (OSM)", "Energy", False),
}


def _geojson(gdf: gpd.GeoDataFrame) -> bytes:
    """GeoJSON with attrs as nested objects and coordinates rounded to 1e-6° (~0.1 m)."""
    out = gdf.copy()
    out["geometry"] = shapely.transform(out.geometry.values, lambda c: np.round(c, 6))
    out["attrs"] = out["attrs"].map(json.loads)
    out["in_pilot"] = out["in_pilot"].astype(bool)
    # allow_nan=False: NaN is not valid JSON and breaks browsers — fail loudly at startup instead.
    return out.to_json(drop_id=True, na="drop", allow_nan=False).encode()


@dataclass
class Layer:
    id: str
    gdf: gpd.GeoDataFrame
    full: bytes
    pilot: bytes

    def meta(self) -> dict:
        title, group, visible = LAYER_META.get(self.id, (self.id, "Other", False))
        return {
            "id": self.id, "title": title, "group": group, "default_visible": visible,
            "geometry_type": sorted(set(self.gdf.geom_type)),
            "count": len(self.gdf), "count_in_pilot": int(self.gdf["in_pilot"].astype(bool).sum()),
            "data_status": dict(Counter(self.gdf["data_status"])),
            "source_ids": sorted(set(self.gdf["source_id"])),
        }


@dataclass
class LayerStore:
    path: Path
    layers: dict[str, Layer] = field(default_factory=dict)
    index: dict[str, tuple[str, int]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = GPKG) -> LayerStore:
        """Base GPKG first, then every other domain GPKG next to it (drainage.gpkg, …; one per domain, < 5 MB)."""
        store = cls(path)
        if not path.exists():
            return store
        files = [path] + sorted(p for p in path.parent.glob("*.gpkg") if p != path)
        found = [(n, f) for f in files for n, _ in pyogrio.list_layers(f)]
        data = path.parents[1]
        extra = [("sites", [data / "curated" / "sites.geojson"]),  # P09 curated candidate sites
                 # P11: curated measurements win over the demo file when they exist
                 ("water_quality", [data / "curated" / "water_quality.geojson", data / "synthetic" / "water_quality.geojson"])]
        for name, candidates in extra:
            src = next((c for c in candidates if c.exists()), None)
            if src:
                found.append((name, src))
        order = {n: i for i, n in enumerate(LAYER_META)}
        for name, f in sorted(found, key=lambda nf: order.get(nf[0], 99)):
            if name in store.layers:
                raise ValueError(f"layer {name!r} defined in two GeoPackages")
            gdf = gpd.read_file(f) if f.suffix == ".geojson" else gpd.read_file(f, layer=name)
            if f.suffix == ".geojson":  # GDAL parses JSON-looking strings into dicts; keep the GPKG convention (text)
                gdf["attrs"] = gdf["attrs"].map(lambda a: a if isinstance(a, str) else json.dumps(a))
                for col in gdf.columns:  # …and ISO strings into Timestamps
                    if str(gdf[col].dtype).startswith("datetime"):
                        gdf[col] = gdf[col].map(lambda t: t.isoformat() if t == t and t is not None else None)
            store.layers[name] = Layer(name, gdf, _geojson(gdf), _geojson(gdf[gdf["in_pilot"].astype(bool)]))
            store.index.update({aid: (name, i) for i, aid in enumerate(gdf["asset_id"])})
        return store

    def region(self) -> dict | None:
        b = self.layers.get("boundary")
        if b is None:
            return None
        row = b.gdf.iloc[0]
        c = row.geometry.centroid
        return {
            "asset_id": row["asset_id"], "name": row["name"], "data_status": row["data_status"],
            "source_id": row["source_id"], "attrs": json.loads(row["attrs"]),
            "centroid": [round(c.x, 6), round(c.y, 6)],
            "bbox": [round(v, 6) for v in row.geometry.bounds],
            "boundary": json.loads(b.full),
        }

    def asset(self, asset_id: str) -> dict | None:
        hit = self.index.get(asset_id)
        if hit is None:
            return None
        layer, i = hit
        row = self.layers[layer].gdf.iloc[i]
        props = {k: (None if v != v else v) for k, v in row.drop("geometry").to_dict().items()}  # NaN → None
        props["attrs"] = json.loads(props["attrs"])
        props["in_pilot"] = bool(props["in_pilot"])
        c = row.geometry.representative_point()
        return {"layer": layer, **props, "position": [round(c.x, 6), round(c.y, 6)], "relationships": []}


@lru_cache
def get_store() -> LayerStore:
    return LayerStore.load()
