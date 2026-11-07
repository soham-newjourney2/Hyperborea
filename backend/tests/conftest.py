"""Shared test setup: existing API tests run as an authenticated admin (P15 guard); test_auth.py tests the guard itself."""
import pytest

from backend.app.core.security import require_admin
from backend.app.main import app


@pytest.fixture(autouse=True)
def _admin(request):
    if request.node.get_closest_marker("real_auth"):
        app.dependency_overrides.pop(require_admin, None)
        yield
        return
    app.dependency_overrides[require_admin] = lambda: {"role": "admin", "sub": "test"}
    yield
    app.dependency_overrides.pop(require_admin, None)


def pytest_configure(config):
    config.addinivalue_line("markers", "real_auth: run without the test admin override")
