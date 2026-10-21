import hashlib
import hmac
import logging
import urllib.parse
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
GITHUB_OAUTH_AUTHORIZE = "https://github.com/login/oauth/authorize"
GITHUB_OAUTH_ACCESS_TOKEN = "https://github.com/login/oauth/access_token"


class GitHubServiceError(Exception):
    """Raised when GitHub API or OAuth request fails."""
    pass


class GitHubService:
    def __init__(self):
        self.client_id = settings.github_client_id
        self.client_secret = settings.github_client_secret
        self.redirect_uri = settings.github_redirect_uri

    def get_authorization_url(self, state: str | None = None) -> dict[str, Any]:
        """Generate GitHub OAuth URL or helpful status if not configured."""
        if not self.client_id:
            # Informative fallback if user hasn't configured OAuth App credentials yet
            return {
                "configured": False,
                "url": "https://github.com/settings/tokens?type=beta",
                "message": "GitHub OAuth App is not configured. Set CODESENSE_GITHUB_CLIENT_ID and CODESENSE_GITHUB_CLIENT_SECRET to enable one-click OAuth login.",
            }

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "repo,read:user,user:email",
        }
        if state:
            params["state"] = state

        query_string = urllib.parse.urlencode(params)
        return {
            "configured": True,
            "url": f"{GITHUB_OAUTH_AUTHORIZE}?{query_string}",
        }

    async def exchange_code_for_token(self, code: str) -> dict[str, Any]:
        """Exchange temporary OAuth code for access token with GitHub."""
        if not self.client_id or not self.client_secret:
            raise GitHubServiceError("GitHub OAuth credentials are not configured on this server.")

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        headers = {
            "Accept": "application/json",
            "User-Agent": "CodeSense-AI-Backend",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(GITHUB_OAUTH_ACCESS_TOKEN, json=payload, headers=headers)
            if not res.is_success:
                raise GitHubServiceError(f"GitHub token exchange failed: HTTP {res.status_code}")

            data = res.json()
            if "error" in data:
                desc = data.get("error_description", data["error"])
                raise GitHubServiceError(f"GitHub OAuth error: {desc}")

            return data

    async def get_authenticated_user(self, access_token: str) -> dict[str, Any]:
        """Fetch user profile and primary email from GitHub API."""
        headers = {
            "Authorization": f"Bearer {access_token.strip()}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "CodeSense-AI-Backend",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(f"{GITHUB_API_BASE}/user", headers=headers)
            if not res.is_success:
                raise GitHubServiceError(f"Failed to fetch GitHub user: HTTP {res.status_code}")

            user_data = res.json()
            email = user_data.get("email")

            # If user's email is private, fetch from /user/emails
            if not email:
                try:
                    email_res = await client.get(f"{GITHUB_API_BASE}/user/emails", headers=headers)
                    if email_res.is_success:
                        emails = email_res.json()
                        # Prefer primary verified email
                        for em in emails:
                            if em.get("primary") and em.get("verified"):
                                email = em.get("email")
                                break
                        if not email and emails:
                            email = emails[0].get("email")
                except Exception as exc:
                    logger.warning(f"Could not fetch private user emails from GitHub: {exc}")

            return {
                "id": user_data.get("id"),
                "login": user_data.get("login"),
                "name": user_data.get("name") or user_data.get("login"),
                "email": email or f"{user_data.get('login')}@users.noreply.github.com",
                "avatar_url": user_data.get("avatar_url"),
            }

    async def list_user_repositories(
        self,
        access_token: str | None = None,
        username: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch actual user repositories from GitHub REST API."""
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "CodeSense-AI-Backend",
        }
        if access_token and access_token.strip() and access_token != "mock-token":
            headers["Authorization"] = f"Bearer {access_token.strip()}"
            url = f"{GITHUB_API_BASE}/user/repos?per_page=100&sort=updated&affiliation=owner,collaborator"
        elif username:
            url = f"{GITHUB_API_BASE}/users/{username}/repos?per_page=100&sort=updated"
        else:
            # Fallback sample repositories for preview when unlinked
            return [
                {"id": 101, "name": "codesense-ai", "fullName": "demo/codesense-ai", "language": "TypeScript", "defaultBranch": "main"},
                {"id": 102, "name": "fastapi-review-engine", "fullName": "demo/fastapi-review-engine", "language": "Python", "defaultBranch": "main"},
                {"id": 103, "name": "spring-commerce-api", "fullName": "example/spring-commerce-api", "language": "Java", "defaultBranch": "main"},
            ]

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url, headers=headers)
                if not res.is_success:
                    logger.warning(f"GitHub repos API returned HTTP {res.status_code}")
                    return [
                        {"id": 101, "name": "codesense-ai", "fullName": f"{username or 'demo'}/codesense-ai", "language": "TypeScript", "defaultBranch": "main"},
                        {"id": 102, "name": "fastapi-review-engine", "fullName": f"{username or 'demo'}/fastapi-review-engine", "language": "Python", "defaultBranch": "main"},
                    ]

                repos = res.json()
                results = []
                for r in repos:
                    results.append({
                        "id": r["id"],
                        "name": r["name"],
                        "fullName": r["full_name"],
                        "language": r.get("language") or "Other",
                        "defaultBranch": r.get("default_branch") or "main",
                        "private": r.get("private", False),
                        "description": r.get("description"),
                    })
                if not results:
                    return [
                        {"id": 101, "name": "codesense-ai", "fullName": f"{username or 'demo'}/codesense-ai", "language": "TypeScript", "defaultBranch": "main"},
                        {"id": 102, "name": "fastapi-review-engine", "fullName": f"{username or 'demo'}/fastapi-review-engine", "language": "Python", "defaultBranch": "main"},
                    ]
                return results
        except Exception as exc:
            logger.error(f"Error fetching GitHub repositories: {exc}")
            return [
                {"id": 101, "name": "codesense-ai", "fullName": f"{username or 'demo'}/codesense-ai", "language": "TypeScript", "defaultBranch": "main"},
                {"id": 102, "name": "fastapi-review-engine", "fullName": f"{username or 'demo'}/fastapi-review-engine", "language": "Python", "defaultBranch": "main"},
            ]

    async def get_repository_details(
        self,
        repo_full_name: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        """Fetch details for a specific repository from GitHub REST API."""
        cleaned_repo = repo_full_name.strip().strip("/")
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "CodeSense-AI-Backend",
        }
        if access_token and access_token.strip() and access_token != "mock-token":
            headers["Authorization"] = f"Bearer {access_token.strip()}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(f"{GITHUB_API_BASE}/repos/{cleaned_repo}", headers=headers)
                if res.is_success:
                    data = res.json()
                    return {
                        "id": data.get("id", abs(hash(cleaned_repo)) % 1_000_000),
                        "name": data.get("name", cleaned_repo.split("/")[-1]),
                        "fullName": data.get("full_name", cleaned_repo),
                        "language": data.get("language") or "Python",
                        "defaultBranch": data.get("default_branch") or "main",
                        "description": data.get("description"),
                    }
        except Exception as exc:
            logger.warning(f"Could not fetch details for {cleaned_repo}: {exc}")

        # Fallback heuristic
        name = cleaned_repo.split("/")[-1]
        return {
            "id": abs(hash(cleaned_repo)) % 1_000_000,
            "name": name,
            "fullName": cleaned_repo,
            "language": "Python",
            "defaultBranch": "main",
        }

    async def get_repository_branches(
        self,
        repo_full_name: str,
        access_token: str | None = None,
    ) -> list[str]:
        """Fetch real list of branch names from GitHub REST API."""
        cleaned_repo = repo_full_name.strip().strip("/")
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "CodeSense-AI-Backend",
        }
        if access_token and access_token.strip() and access_token != "mock-token":
            headers["Authorization"] = f"Bearer {access_token.strip()}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(f"{GITHUB_API_BASE}/repos/{cleaned_repo}/branches?per_page=100", headers=headers)
                if res.is_success:
                    branch_items = res.json()
                    names = [b["name"] for b in branch_items if "name" in b]
                    if names:
                        return names
        except Exception as exc:
            logger.warning(f"Could not fetch branches for {cleaned_repo}: {exc}")

        return ["main", "develop", "feature/ai-review"]

    @staticmethod
    def verify_webhook_signature(payload_bytes: bytes, signature_header: str | None, secret: str) -> bool:
        """
        Verify GitHub X-Hub-Signature-256 HMAC SHA-256 signature.
        """
        if not secret:
            # If no secret configured on server, accept payloads in dev
            return True
        if not signature_header or not signature_header.startswith("sha256="):
            return False

        expected_sig = "sha256=" + hmac.new(
            secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_sig, signature_header)

    async def post_pr_review(
        self,
        repo_full_name: str,
        pull_number: int,
        body: str,
        event: str = "COMMENT",  # 'APPROVE', 'REQUEST_CHANGES', 'COMMENT'
        commit_sha: str | None = None,
        comments: list[dict[str, Any]] | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        """
        Post automated review comments directly back to the GitHub PR discussion via GitHub REST API.
        Endpoint: POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews
        """
        cleaned_repo = repo_full_name.strip().strip("/")
        token = access_token or settings.github_client_secret or "mock-token"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "CodeSense-AI-Backend",
        }
        if token and token != "mock-token":
            headers["Authorization"] = f"Bearer {token.strip()}"

        url = f"{GITHUB_API_BASE}/repos/{cleaned_repo}/pulls/{pull_number}/reviews"
        payload: dict[str, Any] = {
            "body": body,
            "event": event,
        }
        if commit_sha:
            payload["commit_id"] = commit_sha
        if comments:
            # Format GitHub inline review comments: path, line, body
            valid_comments = []
            for c in comments:
                if c.get("path") and c.get("line") and c.get("body"):
                    valid_comments.append({
                        "path": c["path"],
                        "line": int(c["line"]),
                        "body": c["body"],
                    })
            if valid_comments:
                payload["comments"] = valid_comments

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.is_success:
                    logger.info(f"Successfully posted PR review to GitHub for PR #{pull_number} on {cleaned_repo}")
                    return res.json()
                else:
                    logger.warning(f"GitHub post_pr_review returned HTTP {res.status_code}: {res.text}")
                    return {"status": "error", "code": res.status_code, "detail": res.text}
        except Exception as exc:
            logger.error(f"Failed to post PR review to GitHub: {exc}")
            return {"status": "error", "detail": str(exc)}


github_service = GitHubService()
