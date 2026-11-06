from fastapi.testclient import TestClient

from backend.app.main import app


def test_health():
    r = TestClient(app).get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert {"status", "version", "data_timestamp"} <= body.keys()
