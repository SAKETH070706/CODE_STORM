"""Bound streamed request bodies, including chunked uploads, before multipart parsing."""
import asyncio
import time
from starlette.responses import JSONResponse

class BodyLimit:
    def __init__(self, app, limit=2 * 1024 * 1024):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        limit = 16384 if scope["path"] in ("/api/actions", "/api/authorize") else self.limit
        messages, size = [], 0
        deadline = time.monotonic() + 10
        while True:
            try:
                message = await asyncio.wait_for(receive(), max(.001, deadline - time.monotonic()))
            except (TimeoutError, asyncio.TimeoutError):
                from starlette.requests import Request
                from api.main import rejected_request
                response = await rejected_request(Request(scope), 408, "Request body deadline exceeded")
                return await response(scope, receive, send)
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > limit:
                from starlette.requests import Request
                from api.main import rejected_request
                response = await rejected_request(Request(scope), 413, "Request body too large")
                return await response(scope, receive, send)
            messages.append(message)
            if not message.get("more_body", False):
                break
        async def replay():
            return messages.pop(0) if messages else {"type": "http.request", "body": b"", "more_body": False}
        await self.app(scope, replay, send)


