"""Thresholds + weights from config/ (single source for engine and UI)."""
from functools import lru_cache

import yaml

from backend.app.core.paths import CONFIG


@lru_cache
def flood_rules() -> dict:
    return yaml.safe_load((CONFIG / "flood.yaml").read_text(encoding="utf-8"))


@lru_cache
def risk_rules() -> dict:
    return yaml.safe_load((CONFIG / "risk.yaml").read_text(encoding="utf-8"))
