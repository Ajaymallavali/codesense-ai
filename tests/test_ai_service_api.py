import pytest
from app.schemas import PrReviewResponse


@pytest.mark.asyncio
async def test_ai_service_health(ai_client):
    response = await ai_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"service": "codesense-ai-service", "status": "UP"}


@pytest.mark.asyncio
async def test_ai_service_sample_analyze(ai_client):
    payload = {
        "repository_url": "example/fastapi-review-engine",
        "branch": "main",
    }
    response = await ai_client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["repository"] == "example/fastapi-review-engine"
    assert data["maintainability_score"] > 80
    assert isinstance(data["findings"], list)
    assert len(data["findings"]) >= 3


@pytest.mark.asyncio
async def test_ai_service_chat_with_ast_findings(ai_client):
    payload = {
        "repository_url": "example/fastapi-review-engine",
        "branch": "main",
        "query": "Show me the detected security issues",
        "maintainability_score": 85,
        "technical_debt_hours": 12,
        "findings": [
            {
                "category": "Security",
                "severity": "High",
                "file": "app/auth.py",
                "title": "Hardcoded JWT secret detected",
                "suggestion": "Read secret from environment variable",
                "line_number": 42,
            }
        ],
    }
    response = await ai_client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["response"]) > 20


@pytest.mark.asyncio
async def test_ai_service_explain(ai_client):
    payload = {
        "repository_url": "example/fastapi-review-engine",
        "branch": "main",
        "category": "Security",
        "severity": "High",
        "file_path": "app/auth.py",
        "title": "Hardcoded JWT secret detected",
        "suggestion": "Read secret from environment variable",
        "line_number": 42,
        "code_snippet": "SECRET_KEY = 'super-secret-123'",
    }
    response = await ai_client.post("/explain", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "explanation" in data
    assert "suggestion" in data
    assert "SECRET_KEY" in data["suggestion"] or "environ" in data["suggestion"] or "python" in data["suggestion"]


@pytest.mark.asyncio
async def test_ai_service_review_pr(ai_client):
    payload = {
        "repository_url": "example/fastapi-review-engine",
        "branch": "feature/security-hardening",
        "base_branch": "main",
        "pr_title": "PR: Harden token authentication",
        "diff_or_code": "diff --git a/app/auth.py b/app/auth.py",
        "maintainability_score": 75,
        "technical_debt_hours": 14,
        "findings": [
            {
                "category": "Security",
                "severity": "High",
                "file": "app/auth.py",
                "title": "Unsafe token generation",
                "suggestion": "Use cryptographically secure secrets module",
                "line_number": 28,
            }
        ],
    }
    response = await ai_client.post("/review/pr", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] in ("APPROVE", "REQUEST_CHANGES", "COMMENT")
    assert data["risk_level"] in ("Low", "Medium", "High", "Critical")
    assert isinstance(data["inline_comments"], list)
    assert len(data["inline_comments"]) > 0
    assert len(data["suggested_improvements"]) > 0
