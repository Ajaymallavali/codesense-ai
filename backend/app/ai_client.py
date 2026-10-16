import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AiClientError(Exception):
    """Raised when communication with the AI service fails."""
    pass


class AiClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.ai_service_url).rstrip("/")

    async def check_health(self) -> dict[str, Any]:
        """Check if AI Service is responsive."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/health")
                if res.is_success:
                    return res.json()
                return {"status": "DOWN", "statusCode": res.status_code}
        except Exception as exc:
            logger.warning(f"AI Service health check failed: {exc}")
            return {"status": "DOWN", "error": str(exc)}

    async def analyze_repository(
        self,
        repo_url: str,
        branch: str = "main",
        github_token: str | None = None,
    ) -> dict[str, Any]:
        """Request deep static analysis and debt assessment from AI Service."""
        payload = {
            "repository_url": repo_url,
            "branch": branch,
            "github_token": github_token,
        }
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                logger.info(f"Calling AI service /analyze for {repo_url} (branch: {branch})")
                res = await client.post(f"{self.base_url}/analyze", json=payload)
                if not res.is_success:
                    detail = res.text
                    try:
                        detail = res.json().get("detail", detail)
                    except Exception:
                        pass
                    raise AiClientError(f"AI Service returned HTTP {res.status_code}: {detail}")
                return res.json()
        except httpx.RequestError as exc:
            logger.error(f"Network error calling AI service: {exc}")
            raise AiClientError(f"Could not connect to AI Service at {self.base_url}: {exc}") from exc

    async def chat(
        self,
        repo_url: str,
        branch: str = "main",
        query: str = "",
        maintainability_score: int | None = None,
        technical_debt_hours: int | None = None,
        findings: list[dict[str, Any]] | None = None,
        code_context: str | None = None,
        github_token: str | None = None,
    ) -> str:
        """Forward repository context chat query to AI Service."""
        payload = {
            "repository_url": repo_url,
            "branch": branch,
            "github_token": github_token,
            "query": query,
            "maintainability_score": maintainability_score,
            "technical_debt_hours": technical_debt_hours,
            "findings": findings,
            "code_context": code_context,
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(f"{self.base_url}/chat", json=payload)
                if res.is_success:
                    data = res.json()
                    return data.get("response", "No response text returned.")
                logger.warning(f"AI Service chat error {res.status_code}: {res.text}")
                return f"AI Service response error ({res.status_code}): {res.text}"
        except Exception as exc:
            logger.error(f"AI Service chat failed: {exc}")
            return f"Unable to reach CodeSense AI service: {str(exc)}"

    async def explain(
        self,
        repo_url: str,
        branch: str = "main",
        finding: dict[str, Any] | None = None,
        code_snippet: str | None = None,
        github_token: str | None = None,
    ) -> dict[str, str]:
        """Ask AI service for detailed explanation and code fix suggestion."""
        f = finding or {}
        payload = {
            "repository_url": repo_url,
            "branch": branch,
            "github_token": github_token,
            "category": f.get("category", "General"),
            "severity": f.get("severity", "Medium"),
            "file_path": f.get("file_path", f.get("file", "unknown")),
            "title": f.get("title", "Issue"),
            "suggestion": f.get("suggestion", ""),
            "line_number": f.get("line_number", 1) or 1,
            "code_snippet": code_snippet or f.get("code_snippet"),
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(f"{self.base_url}/explain", json=payload)
                if res.is_success:
                    return res.json()
                return {
                    "explanation": f"AI service error ({res.status_code}): {res.text}",
                    "suggestion": "Could not generate suggested fix.",
                }
        except Exception as exc:
            logger.error(f"AI Service explain failed: {exc}")
            return {
                "explanation": f"Failed to contact AI service: {str(exc)}",
                "suggestion": "Could not generate suggested fix.",
            }

    async def review_pr(
        self,
        repo_url: str,
        branch: str = "main",
        base_branch: str = "main",
        pr_title: str | None = None,
        pr_description: str | None = None,
        diff_or_code: str | None = None,
        findings: list[dict[str, Any]] | None = None,
        maintainability_score: int | None = None,
        technical_debt_hours: int | None = None,
        github_token: str | None = None,
    ) -> dict[str, Any]:
        """Request automated PR review with inline suggestions and verdict."""
        payload = {
            "repository_url": repo_url,
            "branch": branch,
            "base_branch": base_branch,
            "pr_title": pr_title,
            "pr_description": pr_description,
            "diff_or_code": diff_or_code,
            "findings": findings,
            "maintainability_score": maintainability_score,
            "technical_debt_hours": technical_debt_hours,
            "github_token": github_token,
        }
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                res = await client.post(f"{self.base_url}/review/pr", json=payload)
                if res.is_success:
                    return res.json()
                logger.warning(f"AI Service PR review error {res.status_code}: {res.text}")
                return {
                    "summary": f"AI review returned error {res.status_code}: {res.text}",
                    "verdict": "COMMENT",
                    "risk_level": "Medium",
                    "inline_comments": [],
                    "suggested_improvements": ["Check AI service logs and retry."],
                }
        except Exception as exc:
            logger.error(f"AI Service PR review failed: {exc}")
            return {
                "summary": f"Could not connect to AI service: {str(exc)}",
                "verdict": "COMMENT",
                "risk_level": "Medium",
                "inline_comments": [],
                "suggested_improvements": ["Ensure AI service is running and accessible."],
            }


ai_client = AiClient()
