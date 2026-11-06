"""Overpass fallback: clip OSM data out of a Geofabrik .osm.pbf extract (same data, file access).

Used by fetch_osm.py when Overpass is unavailable (P02, 2026-11-06: public mirrors down / 502 / timeouts).
Writes three .osm XML files for osmnx: features.osm (tagged objects for layers), drive.osm, walk.osm
(ways passing osmnx's own network filters, parsed from its Overpass filter strings).
"""
from __future__ import annotations

import re
from pathlib import Path

import httpx
import osmium
from osmium.filter import KeyFilter
from osmnx import _overpass

from pipelines.osm_common import ROOT

PBF_URL = "https://download.geofabrik.de/asia/india/eastern-zone-261104.osm.pbf"  # Geofabrik, 2026-11-05
PBF_DIR = ROOT / "local" / "osm"
KEYS = ("building", "highway", "amenity", "railway", "station", "power", "waterway", "natural", "landuse",
        "public_transport", "subway")
UA = {"User-Agent": "Hyperborea/0.1 (hackathon research pipeline)"}


def ensure_pbf(url: str = PBF_URL) -> Path:
    path = PBF_DIR / url.rsplit("/", 1)[-1]
    if path.exists():
        return path
    PBF_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    print(f"  downloading {url} …", flush=True)
    with httpx.stream("GET", url, headers=UA, follow_redirects=True, timeout=120) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
    tmp.rename(path)
    print(f"  saved {path.relative_to(ROOT)} ({path.stat().st_size / 1e6:.0f} MB)", flush=True)
    return path


def network_filter(net: str):
    """Turn osmnx's Overpass filter (e.g. ["highway"]["area"!~"yes"]) into a predicate on tags."""
    rules = re.findall(r'\["([^"]+)"(?:(!~)"([^"]*)")?\]', _overpass._get_network_filter(net))

    def ok(tags) -> bool:
        for key, op, rx in rules:
            v = tags.get(key)
            if not op and v is None:
                return False
            if op and v is not None and re.search(rx, v):
                return False
        return True

    return ok


def clip(pbf: Path, bbox: tuple[float, float, float, float], out_dir: Path) -> dict[str, Path]:
    w, s, e, n = bbox
    inside = lambda loc: loc.valid() and w <= loc.lon <= e and s <= loc.lat <= n  # noqa: E731
    paths = {k: out_dir / f"{k}.osm" for k in ("features", "drive", "walk")}
    nets = {"drive": network_filter("drive"), "walk": network_filter("walk")}

    # Pass 1: relations with relevant keys → member way ids (multipolygon outers are often untagged).
    rel_ways: dict[int, set[int]] = {}
    for r in osmium.FileProcessor(pbf, osmium.osm.RELATION).with_filter(KeyFilter(*KEYS)):
        rel_ways[r.id] = {m.ref for m in r.members if m.type == "w"}
    way_rels: dict[int, list[int]] = {}
    for rid, ways in rel_ways.items():
        for wid in ways:
            way_rels.setdefault(wid, []).append(rid)

    # Pass 2: tagged nodes + ways inside the bbox (node locations resolved by osmium).
    keep_rels: set[int] = set()
    writers = {k: osmium.BackReferenceWriter(str(p), ref_src=str(pbf), overwrite=True) for k, p in paths.items()}
    try:
        fp = (osmium.FileProcessor(pbf, osmium.osm.NODE | osmium.osm.WAY).with_locations()
              .with_filter(KeyFilter(*KEYS).enable_for(osmium.osm.NODE)))
        for o in fp:
            if o.is_node():
                if inside(o.location):
                    writers["features"].add_node(o)
                continue
            if not any(inside(nr.location) for nr in o.nodes):
                continue
            if o.id in way_rels:
                keep_rels.update(way_rels[o.id])
            tags = dict(o.tags)
            if any(k in tags for k in KEYS):
                writers["features"].add_way(o)
            if "highway" in tags:
                for net, ok in nets.items():
                    if ok(tags):
                        writers[net].add_way(o)
        # Pass 3: the relations that touch the bbox.
        for r in osmium.FileProcessor(pbf, osmium.osm.RELATION).with_filter(KeyFilter(*KEYS)):
            if r.id in keep_rels:
                writers["features"].add_relation(r)
    finally:
        for wr in writers.values():
            wr.close()  # back-references (way nodes, relation members) are resolved here
    print(f"  clipped: {len(keep_rels)} relations; files {[p.name for p in paths.values()]}", flush=True)
    return paths
