"""P16: pure-ASGI middleware — `?region=<id>` sets the request-scoped region (unknown → 404)."""
from __future__ import annotations

import json
from urllib.parse import parse_qs

from . import regions


class RegionMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        qs = parse_qs(scope.get("query_string", b"").decode("latin-1"))
        rid = (qs.get("region") or [regions.DEFAULT])[0]
        try:
            token = regions.set_current(rid)
        except KeyError:
            body = json.dumps({"detail": f"Unknown region {rid!r}"}).encode()
            await send({"type": "http.response.start", "status": 404,
                        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
            await send({"type": "http.response.body", "body": body})
            return
        try:
            await self.app(scope, receive, send)
        finally:
            regions.reset(token)
