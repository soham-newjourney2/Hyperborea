from datetime import datetime, timezone

from fastapi import APIRouter

from ..core.config import VERSION
from ..core.paths import GPKG

router = APIRouter()


@router.get("/health")
def health() -> dict:
    data_ts = None
    if GPKG.exists():
        data_ts = datetime.fromtimestamp(GPKG.stat().st_mtime, tz=timezone.utc).isoformat()
    return {"status": "ok", "version": VERSION, "data_timestamp": data_ts}
