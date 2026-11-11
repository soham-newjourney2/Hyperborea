"""P24: POST /ask — plain-language question about the active region → engine run → grounded answer."""
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...engine import ask as ea
from ...engine import explain as ex
from ..core.config import get_settings
from .insight import _model
from .scenarios import attach_access, flood_context, result_cache
from .weather import presets_data

router = APIRouter()


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=400)
    mode: Literal["template", "llm"] | None = None


@router.post("/ask")
def ask(req: AskRequest) -> dict:
    s = get_settings()
    mode = req.mode or s.explainer
    ctx = flood_context()
    llm_ok = mode == "llm" and ex.llm_status(s.ollama_url, _model())["available"]

    def run(params: dict) -> dict:
        return attach_access(result_cache().get_or_run(ctx, params))

    return ea.ask(req.question, presets_data(), run, ctx.fac, mode, s.ollama_url, _model(), llm_ok)
