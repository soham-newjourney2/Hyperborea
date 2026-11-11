"""P16 multi-region registry (config/regions.yaml, D-22).

The active region is request-scoped: `RegionMiddleware` (main.py) sets it from `?region=` (default `sector_v`);
pipelines and scripts pick it from `HYPERBOREA_REGION`. `per_region` caches a zero-argument loader once per region.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from contextvars import ContextVar
from functools import lru_cache, wraps
from pathlib import Path
from threading import Lock
from typing import TypeVar

import yaml

from .paths import CONFIG, DATA, LOCAL, ROOT

T = TypeVar("T")


@lru_cache
def _config() -> dict:
    return yaml.safe_load((CONFIG / "regions.yaml").read_text(encoding="utf-8"))


def registry() -> dict[str, dict]:
    return {r["id"]: r for r in _config()["regions"]}


DEFAULT: str = _config()["default"]
_current: ContextVar[str] = ContextVar("hyperborea_region", default=os.environ.get("HYPERBOREA_REGION") or DEFAULT)


def current() -> str:
    return _current.get()


def set_current(region_id: str):
    """Returns a token for `reset`. Raises KeyError for unknown regions."""
    if region_id not in registry():
        raise KeyError(region_id)
    return _current.set(region_id)


def reset(token) -> None:
    _current.reset(token)


def cfg(region_id: str | None = None) -> dict:
    return registry()[region_id or current()]


def metric_crs(region_id: str | None = None) -> int:
    return int(cfg(region_id)["metric_crs"])


def region_root(region_id: str | None = None) -> Path:
    """data/regions/<id> — every region (Sector V included) has its own folder (layout of 2026-11-11)."""
    return DATA / "regions" / (region_id or current())


def data_dir(kind: str = "processed", region_id: str | None = None) -> Path:
    """data/regions/<id>/<kind> — kind: raw, processed, curated, synthetic, snapshots."""
    return region_root(region_id) / kind


def local_dir(kind: str, region_id: str | None = None) -> Path:
    """local/regions/<id>/<kind> — osm (Geofabrik extract), rasters (DEM), cache (weather/air)."""
    return LOCAL / "regions" / (region_id or current()) / kind


def model_dir(region_id: str | None = None) -> Path:
    """models/regions/<id> — surrogate + metrics + model cards of that region."""
    return ROOT / "models" / "regions" / (region_id or current())


def is_ready(region_id: str) -> bool:
    return (data_dir("processed", region_id) / "hyperborea.gpkg").exists()


def per_region(fn: Callable[[], T]) -> Callable[[], T]:
    """Cache a zero-argument loader per active region (replaces @lru_cache on singletons)."""
    cache: dict[str, T] = {}
    lock = Lock()

    @wraps(fn)
    def wrapper() -> T:
        rid = current()
        if rid not in cache:
            with lock:
                if rid not in cache:
                    cache[rid] = fn()
        return cache[rid]

    wrapper.cache_clear = cache.clear  # type: ignore[attr-defined]
    return wrapper
