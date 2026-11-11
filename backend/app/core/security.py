"""P15 admin auth: password → JWT (role claim, 12 h). Constant-time password compare; RBAC-ready role check."""
from __future__ import annotations

import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings

ALGO = "HS256"
TTL = timedelta(hours=12)
MIN_SECRET = 32  # RFC 7518 §3.2: HS256 key ≥ 256 bits
DEFAULT_PASSWORD = "change-me"
DEFAULT_SECRET = "change-me-long-random"
_bearer = HTTPBearer(auto_error=False)
log = logging.getLogger("hyperborea.auth")


@lru_cache
def signing_key() -> str:
    """Configured JWT_SECRET, or a random per-process key if it is the default / too short (tokens end on restart)."""
    s = get_settings().jwt_secret
    if s == DEFAULT_SECRET or len(s.encode()) < MIN_SECRET:
        log.warning("JWT_SECRET unset or < %d bytes — using a random per-process key", MIN_SECRET)
        return secrets.token_urlsafe(48)
    return s


def password_configured() -> bool:
    """Hosted (HF Space sets SPACE_ID) refuses the default password; locally it is allowed for development."""
    return not (os.environ.get("SPACE_ID") and get_settings().admin_password == DEFAULT_PASSWORD)


def check_password(password: str) -> bool:
    return hmac.compare_digest(password.encode(), get_settings().admin_password.encode())


def create_token(role: str = "admin") -> tuple[str, datetime]:
    exp = datetime.now(timezone.utc) + TTL
    token = jwt.encode({"sub": "hyperborea-admin", "role": role, "exp": exp}, signing_key(), algorithm=ALGO)
    return token, exp


OPEN = {"sub": "public", "role": "admin", "auth": "disabled"}


def require_admin(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if not get_settings().auth_required:  # P20 (D-24): open access unless AUTH_REQUIRED=true
        return OPEN
    if cred is None or cred.scheme.lower() != "bearer":
        raise HTTPException(401, "Login required", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = jwt.decode(cred.credentials, signing_key(), algorithms=[ALGO])
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(401, "Session expired — log in again", headers={"WWW-Authenticate": "Bearer"}) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(401, "Invalid token", headers={"WWW-Authenticate": "Bearer"}) from e
    if claims.get("role") != "admin":
        raise HTTPException(403, "Admin role required")
    return claims
