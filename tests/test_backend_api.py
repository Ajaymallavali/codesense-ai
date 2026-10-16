import pytest
from uuid import uuid4
from unittest.mock import patch, MagicMock

from app.github_service import github_service
from app.jobs import check_redis_health


@pytest.mark.asyncio
async def test_health_endpoint(backend_client):
    response = await backend_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "codesense-fastapi-backend"
    assert data["status"] == "UP"
    assert "aiService" in data
    assert "redis" in data


@pytest.mark.asyncio
async def test_github_auth_url_endpoint(backend_client):
    response = await backend_client.get("/api/auth/github/url?state=test_state")
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "configured" in data


@pytest.mark.asyncio
async def test_sample_analysis_endpoint(backend_client):
    response = await backend_client.get("/api/analysis/sample")
    assert response.status_code == 200
    data = response.json()
    assert data["repository"] == "fastapi-review-engine"
    assert data["maintainabilityScore"] == 91
    assert data["bugCount"] == 8
    assert data["securityIssueCount"] == 3


def test_redis_health_fallback():
    status = check_redis_health()
    assert "status" in status
    assert status["status"] in ("ONLINE", "STANDALONE_FALLBACK")


@pytest.mark.asyncio
async def test_github_service_branches():
    branches = await github_service.get_repository_branches("pallets/flask", access_token=None)
    assert isinstance(branches, list)
    assert len(branches) > 0
    assert any("main" in b for b in branches)
