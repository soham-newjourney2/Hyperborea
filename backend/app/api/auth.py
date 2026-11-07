"""P15: POST /auth/login (planning §8) — admin password → JWT."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core.security import TTL, check_password, create_token, password_configured

router = APIRouter()


class LoginRequest(BaseModel):
    password: str


@router.post("/auth/login")
def login(req: LoginRequest) -> dict:
    if not password_configured():
        raise HTTPException(503, "Admin password not configured on this server")
    if not check_password(req.password):
        raise HTTPException(401, "Wrong password")
    token, exp = create_token("admin")
    return {"access_token": token, "token_type": "bearer", "role": "admin", "expires_at": exp.isoformat(),
            "expires_in_s": int(TTL.total_seconds())}
