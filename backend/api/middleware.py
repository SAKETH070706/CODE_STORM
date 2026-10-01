import time
import uuid
from starlette.datastructures import Headers
from config import logger


HEALTH_PATHS = frozenset({"/health", "/ready", "/api/health", "/api/ready"})


class RequestIDMiddleware:
    """
    Pure ASGI middleware that ensures every request has a traceable, sanitized X-Request-ID.
    Captures latency and produces structured access logs without BaseHTTPMiddleware buffering deadlocks.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        headers = Headers(scope=scope)
        raw_id = headers.get("x-request-id")
        if (
            raw_id
            and 1 <= len(raw_id) <= 64
            and raw_id.isascii()
            and raw_id.isprintable()
            and not any(c in "\r\n\t" for c in raw_id)
        ):
            req_id = raw_id
        else:
            req_id = str(uuid.uuid4())

        # Store in scope state so request.state.request_id is populated
        state = scope.setdefault("state", {})
        state["request_id"] = req_id

        path = scope.get("path", "")
        method = scope.get("method", "GET")
        start_time = time.monotonic()
        status_code = [500]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code[0] = message.get("status", 500)
                resp_headers = list(message.get("headers", []))
                resp_headers.append((b"x-request-id", req_id.encode("latin-1")))
                message["headers"] = resp_headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
            duration_ms = (time.monotonic() - start_time) * 1000
            if path not in HEALTH_PATHS:
                logger.info(
                    f"[{req_id}] {method} {path} -> {status_code[0]} ({duration_ms:.1f}ms)"
                )
        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                f"[{req_id}] UNHANDLED ERROR in {method} {path} ({duration_ms:.1f}ms): {exc}",
                exc_info=True
            )
            raise
