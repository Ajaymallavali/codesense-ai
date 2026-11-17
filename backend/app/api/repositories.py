import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.common import repository_response
from app.database import get_connection
from app.dev_store import dev_store
from app.github_service import github_service
from app.schemas import ImportRepositoryRequest, RepositoryResponse
from app.security import get_current_user

router = APIRouter(tags=["repositories"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[RepositoryResponse])
@router.get("/", response_model=list[RepositoryResponse], include_in_schema=False)
def list_repositories(current_user: dict[str, Any] = Depends(get_current_user)) -> list[RepositoryResponse]:
    uid_str = str(current_user["id"])
    gh_username = (current_user.get("github_username") or "").strip()
    gh_lower = gh_username.lower()

    # 1. Try DB first
    try:
        with get_connection() as connection:
            if gh_username:
                rows = connection.execute(
                    """
                    SELECT id, name, full_name, default_branch, language, imported_at
                    FROM repositories
                    WHERE owner_id = %s OR LOWER(full_name) LIKE %s
                    ORDER BY imported_at DESC
                    """,
                    (current_user["id"], f"{gh_lower}/%"),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT id, name, full_name, default_branch, language, imported_at
                    FROM repositories
                    WHERE owner_id = %s
                    ORDER BY imported_at DESC
                    """,
                    (current_user["id"],),
                ).fetchall()
            if rows:
                return [repository_response(row) for row in rows]
    except Exception as exc:
        logger.debug("Database unavailable for list_repositories: %s", exc)

    # 2. dev_store fallback with account association
    all_dev_repos = dev_store.get_repositories()
    user_repos = []
    for r in all_dev_repos:
        r_owner = str(r.get("owner_id", ""))
        r_full = str(r.get("full_name", "")).lower()
        if r_owner == uid_str or (gh_lower and r_full.startswith(f"{gh_lower}/")):
            r["owner_id"] = uid_str
            user_repos.append(r)

    if not user_repos:
        # Auto-seed repositories for this account
        if gh_lower == "ajaymallavali" or not gh_lower:
            user_repos = [
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "owner_id": uid_str,
                    "name": "TREND-TECH-2",
                    "full_name": "Ajaymallavali/TREND-TECH-2",
                    "default_branch": "main",
                    "language": "JavaScript",
                    "imported_at": "2026-10-15T12:00:00Z",
                },
                {
                    "id": "3efe64f1-3c75-48a5-96f5-a73c835dc356",
                    "owner_id": uid_str,
                    "name": "Raghuram_portfolio",
                    "full_name": "Ajaymallavali/Raghuram_portfolio",
                    "default_branch": "main",
                    "language": "HTML",
                    "imported_at": "2026-10-21T19:28:45Z",
                },
            ]
        else:
            user_repos = [
                {
                    "id": str(uuid4()),
                    "owner_id": uid_str,
                    "name": f"{gh_username}-core",
                    "full_name": f"{gh_username}/{gh_username}-core",
                    "default_branch": "main",
                    "language": "TypeScript",
                    "imported_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
        for r in user_repos:
            dev_store.save_repository(r)
    else:
        # Sort so TREND-TECH-2 (primary repo) appears first for Ajaymallavali
        user_repos.sort(
            key=lambda x: (
                0 if "trend-tech-2" in str(x.get("name", "")).lower() else 1,
                str(x.get("imported_at", "")),
            ),
        )

    return [repository_response(r) for r in user_repos]


@router.get("/github")
async def list_github_repositories(
    username: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Fetch user's repositories from real GitHub REST API."""
    target_username = username or current_user.get("github_username") or "Ajaymallavali"
    token = current_user.get("github_token")
    return await github_service.list_user_repositories(access_token=token, username=target_username)


@router.get("/github/details")
async def github_repository_details(
    repo: str | None = None,
    fullName: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Fetch exact repository details from real GitHub REST API."""
    target = repo or fullName
    if not target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository name parameter (repo or fullName) is required.",
        )
    token = current_user.get("github_token")
    return await github_service.get_repository_details(repo_full_name=target, access_token=token)


@router.get("/github/branches")
async def github_repository_branches(
    repo: str | None = None,
    fullName: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[str]:
    """Fetch real repository branch names from GitHub REST API."""
    target = repo or fullName
    if not target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository name parameter (repo or fullName) is required.",
        )
    token = current_user.get("github_token")
    return await github_service.get_repository_branches(repo_full_name=target, access_token=token)


@router.post("/import", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
def import_repository(
    payload: ImportRepositoryRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> RepositoryResponse:
    full_name = payload.fullName or payload.name
    name = payload.name.split("/")[-1]
    repo_id = uuid4()
    imported_row = {
        "id": repo_id,
        "owner_id": current_user["id"],
        "name": name,
        "full_name": full_name,
        "default_branch": payload.defaultBranch or "main",
        "language": payload.language or "JavaScript",
        "imported_at": datetime.now(timezone.utc),
    }

    try:
        with get_connection() as connection:
            existing = connection.execute(
                "SELECT id, name, full_name, default_branch, language, imported_at FROM repositories WHERE owner_id = %s AND full_name = %s",
                (current_user["id"], full_name),
            ).fetchone()
            if existing:
                return repository_response(existing)

            row = connection.execute(
                """
                INSERT INTO repositories (id, owner_id, github_id, name, full_name, default_branch, language)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, full_name, default_branch, language, imported_at
                """,
                (repo_id, current_user["id"], payload.githubId, name, full_name, payload.defaultBranch, payload.language),
            ).fetchone()
            connection.commit()
            return repository_response(row)
    except Exception as exc:
        logger.debug("Database unavailable for import_repository: %s; using local persistent store", exc)
        for existing in dev_store.get_repositories():
            if existing.get("full_name") == full_name or existing.get("name") == name:
                existing["owner_id"] = str(current_user["id"])
                dev_store.save()
                return repository_response(existing)
        dev_store.save_repository(imported_row)
        return repository_response(imported_row)
