import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from config import logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Ensures every request has a traceable X-Request-ID.
    Captures latency and produces structured access logs without logging sensitive data.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID") or request.headers.get("x-request-id")
        if not req_id:
            req_id = str(uuid.uuid4())

        request.state.request_id = req_id
        start_time = time.monotonic()

        try:
            response = await call_next(request)
            duration_ms = (time.monotonic() - start_time) * 1000
            response.headers["X-Request-ID"] = req_id
            
            # Skip high-frequency health checks from polluting logs
            if request.url.path not in ("/health",):
                logger.info(
                    f"[{req_id}] {request.method} {request.url.path} -> {response.status_code} ({duration_ms:.1f}ms)"
                )
            return response
        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                f"[{req_id}] UNHANDLED ERROR in {request.method} {request.url.path} ({duration_ms:.1f}ms): {exc}",
                exc_info=False
            )
            raise
