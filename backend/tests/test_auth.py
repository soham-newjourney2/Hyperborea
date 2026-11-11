"""P15 guard with AUTH_REQUIRED=true: no token → 401, wrong password → 401, token → 200. P20: open by default."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from backend.app.core import security
from backend.app.core.config import get_settings
from backend.app.main import app

pytestmark = pytest.mark.real_auth
client = TestClient(app)


@pytest.fixture(autouse=True)
def _auth_on(request, monkeypatch):
    if "open_access" not in request.node.name:
        monkeypatch.setattr(get_settings(), "auth_required", True)


def test_open_access_by_default():
    assert get_settings().auth_required is False
    assert client.get("/api/health").json()["auth_required"] is False
    assert client.get("/api/layers").status_code == 200  # no token needed


def test_public_endpoints():
    assert client.get("/api/health").status_code == 200


def test_no_token_is_401():
    for path in ("/api/layers", "/api/region", "/api/graph/summary", "/api/models"):
        r = client.get(path)
        assert r.status_code == 401 and r.headers.get("www-authenticate") == "Bearer", path


def test_wrong_password_is_401():
    assert client.post("/api/auth/login", json={"password": "not-the-password"}).status_code == 401


def test_token_grants_access_and_role_claim():
    r = client.post("/api/auth/login", json={"password": get_settings().admin_password})
    assert r.status_code == 200 and r.json()["role"] == "admin"
    tok = r.json()["access_token"]
    assert jwt.decode(tok, security.signing_key(), algorithms=["HS256"])["role"] == "admin"
    assert client.get("/api/layers", headers={"Authorization": f"Bearer {tok}"}).status_code == 200


def test_expired_or_forged_token_is_401():
    key = security.signing_key()
    old = jwt.encode({"role": "admin", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, key, algorithm="HS256")
    forged = jwt.encode({"role": "admin", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, "wrong-secret-of-at-least-32-bytes-xx", algorithm="HS256")
    for t in (old, forged, "garbage"):
        assert client.get("/api/layers", headers={"Authorization": f"Bearer {t}"}).status_code == 401
    viewer = jwt.encode({"role": "viewer", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, key, algorithm="HS256")
    assert client.get("/api/layers", headers={"Authorization": f"Bearer {viewer}"}).status_code == 403


def test_signing_key_is_strong_even_with_default_secret():
    assert len(security.signing_key().encode()) >= security.MIN_SECRET


def test_hosted_space_refuses_default_password(monkeypatch):
    monkeypatch.setenv("SPACE_ID", "user/hyperborea")
    monkeypatch.setattr(get_settings(), "admin_password", security.DEFAULT_PASSWORD)
    assert client.post("/api/auth/login", json={"password": security.DEFAULT_PASSWORD}).status_code == 503
