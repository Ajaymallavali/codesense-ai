import importlib.util
import os
import sys
from pathlib import Path
from typing import AsyncGenerator
from uuid import uuid4

import httpx
import pytest

ROOT = Path(__file__).resolve().parent.parent

# Add backend and ai-service to sys.path
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.main import app as backend_app
from app.security import create_token

# Load ai-service/app/main.py explicitly to avoid package namespace collisions
ai_main_path = ROOT / "ai-service" / "app" / "main.py"
spec = importlib.util.spec_from_file_location("ai_service_app", str(ai_main_path))
ai_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai_module)
ai_service_app = ai_module.app

ast_scanner_path = ROOT / "ai-service" / "app" / "ast_scanner.py"
ast_spec = importlib.util.spec_from_file_location("ai_service_ast_scanner", str(ast_scanner_path))
ast_module = importlib.util.module_from_spec(ast_spec)
ast_spec.loader.exec_module(ast_module)
TreeSitterScanner = ast_module.TreeSitterScanner


@pytest.fixture
def test_user():
    return {
        "id": uuid4(),
        "email": "developer@codesense.dev",
        "display_name": "Senior Engineer",
        "github_username": "octocat",
        "github_token": "mock-github-token-123",
        "created_at": "2026-10-15T12:00:00Z",
    }


@pytest.fixture
def auth_headers(test_user):
    token = create_token(test_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def backend_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    transport = httpx.ASGITransport(app=backend_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def ai_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    transport = httpx.ASGITransport(app=ai_service_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
