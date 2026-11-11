from datetime import datetime, timezone

from fastapi import APIRouter

from ..core.config import VERSION, get_settings
from ..core.regions import current, data_dir

router = APIRouter()


@router.get("/health")
def health() -> dict:
    data_ts, gpkg = None, data_dir() / "hyperborea.gpkg"
    if gpkg.exists():
        data_ts = datetime.fromtimestamp(gpkg.stat().st_mtime, tz=timezone.utc).isoformat()
    return {"status": "ok", "version": VERSION, "data_timestamp": data_ts, "region": current(),
            "auth_required": get_settings().auth_required}
