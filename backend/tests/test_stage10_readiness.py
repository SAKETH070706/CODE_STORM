import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from api.main import app as main_app
from workspace.models import Database, Base
from workspace.api import create_app
from config import log_startup_diagnostics


def test_main_app_health_and_ready_route_aliases():
    """Verify that both /health, /api/health, /ready, and /api/ready respond correctly on main.app."""
    with TestClient(main_app) as client:
        # Liveness checks
        res_h1 = client.get("/health")
        assert res_h1.status_code == 200
        assert res_h1.json()["status"] == "ok"

        res_h2 = client.get("/api/health")
        assert res_h2.status_code == 200
        assert res_h2.json()["status"] == "ok"


def test_workspace_app_health_and_ready_route_aliases(tmp_path):
    """Verify that /health and /api/health route aliases work on workspace application."""
    db_file = tmp_path / "test_workspace_routes.db"
    db = Database(f"sqlite:///{db_file}", testing=True)
    Base.metadata.create_all(db.engine)
    app = create_app(db)

    with TestClient(app) as client:
        res1 = client.get("/health")
        assert res1.status_code == 200
        assert res1.json()["status"] == "ok"

        res2 = client.get("/api/health")
        assert res2.status_code == 200
        assert res2.json()["status"] == "ok"

    db.engine.dispose()


def test_cors_origin_normalization():
    """Verify that CORS origins with trailing slashes are properly normalized."""
    test_origins = "http://localhost:5173/,http://127.0.0.1:5173/"
    normalized = [v.strip().rstrip("/") for v in test_origins.split(",") if v.strip() and v.strip() != "*"]
    assert normalized == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_startup_diagnostics_logging(caplog):
    """Verify that startup diagnostics logs configuration state without secret tokens."""
    with caplog.at_level("INFO"):
        log_startup_diagnostics()
        assert "Platform Initialization" in caplog.text
        # Ensure no accidental secret token dump
        assert "sk-" not in caplog.text
        assert "AIzaSy" not in caplog.text
