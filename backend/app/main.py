from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .api import development, graph, health, layers, scenarios, weather
from .core import paths  # noqa: F401  (sets local cache defaults)
from .core.config import VERSION, get_settings
from .services.layer_store import get_store


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_store()  # load GeoPackages into memory at startup
    graph.get_graph()  # build the relationship graph once (P07)
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
api.include_router(health.router)
api.include_router(layers.router)
api.include_router(weather.router)
api.include_router(graph.router)
api.include_router(scenarios.router)
api.include_router(development.router)
app.include_router(api)
