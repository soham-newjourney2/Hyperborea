from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .api import access, auth, development, environment, graph, health, insight, layers, ml, scenarios, weather
from .core.security import require_admin
from .core import paths  # noqa: F401  (sets local cache defaults)
from .core.config import VERSION, get_settings
from .services.layer_store import get_store


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_store()  # load GeoPackages into memory at startup
    graph.get_graph()  # build the relationship graph once (P07)
    access.get_access()  # baseline travel times (P12)
    ml.sg.load_model()  # surrogate (P13) — first quick-scan stays fast
    yield


app = FastAPI(title="Hyperborea API", version=VERSION, lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=2048)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")
api.include_router(health.router)  # public: status only
api.include_router(auth.router)  # public: login
# P15: everything else requires an admin JWT (RBAC-ready: role claim checked in require_admin)
guard = [Depends(require_admin)]
for r in (layers, weather, graph, scenarios, development, environment, access, ml, insight):
    api.include_router(r.router, dependencies=guard)
app.include_router(api)
