"""Shared osmnx setup: project-local cache + Overpass retry/mirror rotation."""
import os
import time
import warnings
from pathlib import Path

import osmnx as ox

ROOT = Path(os.environ.get("HYPERBOREA_ROOT", Path(__file__).resolve().parents[1]))
ox.settings.cache_folder = os.environ.get("OSMNX_CACHE", str(ROOT / "local" / "cache" / "osmnx"))
ox.settings.use_cache = True
ox.settings.requests_timeout = 300
warnings.filterwarnings("ignore", category=FutureWarning)

# Probed 2026-11-06: private.coffee + kumi.systems unreachable (timeouts); main server slow but up.
OVERPASS = [
    "https://overpass-api.de/api",
    "https://overpass-api.de/api",
    "https://maps.mail.ru/osm/tools/overpass/api",
]


def overpass(fn, *args, tries: int = 8, **kwargs):
    """Call an osmnx downloader, retrying with backoff and rotating Overpass mirrors."""
    wait = 5
    for i in range(tries):
        ox.settings.overpass_url = OVERPASS[i % len(OVERPASS)]
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            if "InsufficientResponseError" in type(e).__name__:
                raise  # genuinely no data, not a server problem
            print(f"  overpass {ox.settings.overpass_url} failed ({type(e).__name__}: {str(e)[:120]}); "
                  f"retry in {wait}s", flush=True)
            time.sleep(wait)
            wait = min(wait * 2, 120)
    raise RuntimeError("Overpass unavailable after retries")
