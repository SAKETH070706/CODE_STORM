"""Tests for Stage 7 Observability, Logging, Metrics & Telemetry."""
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from fastapi.testclient import TestClient
from api.middleware import RequestIDMiddleware, HEALTH_PATHS
from core.llm_client import call_llm, LLMResult
import api.main as main


def test_request_id_middleware_sanitization():
    """Verify that CRLF and oversized request IDs are sanitized to prevent log injection."""
    from fastapi import FastAPI
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    test_app = FastAPI()
    test_app.add_middleware(RequestIDMiddleware)

    @test_app.get("/test")
    def sample_endpoint(request: Request):
        return {"req_id": request.state.request_id}

    with TestClient(test_app) as client:
        # Valid ID preserved
        res_valid = client.get("/test", headers={"X-Request-ID": "trace-abc-123"})
        assert res_valid.status_code == 200
        assert res_valid.headers["X-Request-ID"] == "trace-abc-123"
        assert res_valid.json()["req_id"] == "trace-abc-123"

        # CRLF injection rejected and replaced with UUID4
        res_crlf = client.get("/test", headers={"X-Request-ID": "bad\r\nINJECTED: log"})
        assert res_crlf.status_code == 200
        assert "\r" not in res_crlf.headers["X-Request-ID"]
        assert "\n" not in res_crlf.headers["X-Request-ID"]
        assert res_crlf.headers["X-Request-ID"] != "bad\r\nINJECTED: log"

        # Oversized ID (> 64 chars) rejected and replaced with UUID4
        oversized = "a" * 100
        res_over = client.get("/test", headers={"X-Request-ID": oversized})
        assert res_over.status_code == 200
        assert len(res_over.headers["X-Request-ID"]) <= 64
        assert res_over.headers["X-Request-ID"] != oversized


def test_health_and_ready_api_route_aliases():
    """Verify that both /health, /ready and /api/health, /api/ready aliases return valid responses."""
    from fastapi import FastAPI
    from api.routes.health import router as health_router

    app = FastAPI()
    app.include_router(health_router)

    with patch("api.routes.health.check_database_health", return_value=(True, "connected")):
        with patch("api.routes.health.pinecone_service.check_connection", return_value=(True, "connected")):
            with TestClient(app) as client:
                res_health = client.get("/health")
                assert res_health.status_code == 200
                assert res_health.json()["status"] == "ok"

                res_api_health = client.get("/api/health")
                assert res_api_health.status_code == 200
                assert res_api_health.json()["status"] == "ok"

                res_ready = client.get("/ready")
                assert res_ready.status_code == 200

                res_api_ready = client.get("/api/ready")
                assert res_api_ready.status_code == 200


def test_llm_result_duration_telemetry():
    """Verify that call_llm populates duration_ms in LLMResult."""
    with patch("core.llm_client.GROQ_API_KEY", ""):
        with patch("core.llm_client.GEMINI_API_KEY", ""):
            res = call_llm(system_prompt="sys", user_prompt="usr", deadline_seconds=5.0)
            assert isinstance(res.duration_ms, float)
            assert res.duration_ms >= 0.0


def test_main_app_exposes_request_id_in_cors():
    """Verify that main app returns X-Request-ID header on requests."""
    with TestClient(main.app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        assert "X-Request-ID" in res.headers
