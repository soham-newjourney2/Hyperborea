"""Shared provenance model (planning §6). Ask the user before changing fields."""
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DataStatus(str, Enum):
    observed = "observed"
    curated = "curated"
    modelled = "modelled"
    simulated = "simulated"
    unknown = "unknown"


class FeatureProps(BaseModel):
    asset_id: str
    asset_type: str
    name: str | None = None
    data_status: DataStatus
    source_id: str
    observed_at: datetime | None = None
    ingested_at: datetime
    confidence: float | str | None = None  # 0–1 or low/med/high
    assumptions: str = ""
    attrs: dict[str, Any] = Field(default_factory=dict)
