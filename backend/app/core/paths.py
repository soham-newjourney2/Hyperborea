"""Repo paths + local cache defaults (planning §9). Mirrors scripts/env.ps1 when it wasn't sourced."""
import os
from pathlib import Path

ROOT = Path(os.environ.get("HYPERBOREA_ROOT", Path(__file__).resolve().parents[3]))
LOCAL = ROOT / "local"
DATA = ROOT / "data"
# Default region (Sector V) folders — kept for tests/tools; region-aware code uses core.regions.data_dir()
PROCESSED = DATA / "regions" / "sector_v" / "processed"
GPKG = PROCESSED / "hyperborea.gpkg"
SNAPSHOTS = DATA / "regions" / "sector_v" / "snapshots"
CONFIG = ROOT / "config"

_CACHE_DEFAULTS = {
    "HF_HOME": LOCAL / "hf",
    "TORCH_HOME": LOCAL / "torch",
    "PIP_CACHE_DIR": LOCAL / "cache" / "pip",
    "MPLCONFIGDIR": LOCAL / "cache" / "mpl",
    "OLLAMA_MODELS": LOCAL / "ollama" / "models",
    "OSMNX_CACHE": LOCAL / "cache" / "osmnx",
}
for _k, _v in _CACHE_DEFAULTS.items():
    os.environ.setdefault(_k, str(_v))
