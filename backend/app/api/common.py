from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any
from fastapi import Request
from fastapi.responses import JSONResponse

from app.schemas import (
    AnalysisResponse,
    AuthResponse,
    FindingResponse,
    RepositoryResponse,
    UserResponse,
)
from app.security import create_token


def to_camel(value: str) -> str:
    """Convert snake_case key to camelCase."""
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


def error_response(
    request: Request,
    status_code: int,
    message: str,
    field_errors: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status_code,
            "error": HTTPStatus(status_code).phrase,
            "message": message,
            "path": request.url.path,
            "fieldErrors": field_errors or {},
        },
    )


def user_response(user: dict[str, Any]) -> UserResponse:
    return UserResponse(
        id=user["id"],
        email=user["email"],
        displayName=user["display_name"],
        githubUsername=user.get("github_username"),
        createdAt=user["created_at"],
    )


def auth_response(user: dict[str, Any]) -> AuthResponse:
    return AuthResponse(token=create_token(user), user=user_response(user))


def repository_response(row: dict[str, Any]) -> RepositoryResponse:
    return RepositoryResponse(
        id=row["id"],
        name=row["name"],
        fullName=row["full_name"],
        defaultBranch=row["default_branch"],
        language=row.get("language"),
        importedAt=row["imported_at"],
    )


def analysis_response(row: dict[str, Any]) -> AnalysisResponse:
    return AnalysisResponse(
        id=row["id"],
        repositoryId=row["repository_id"],
        branch=row["branch"],
        maintainabilityScore=row.get("maintainability_score") or 0,
        technicalDebtHours=row.get("technical_debt_hours") or 0,
        status=row["status"],
        progress=row.get("progress") or (100 if row["status"] == "COMPLETED" else 0),
        errorMessage=row.get("error_message"),
        startedAt=row["started_at"],
        completedAt=row.get("completed_at"),
    )


def finding_response(row: dict[str, Any]) -> FindingResponse:
    return FindingResponse(
        id=row["id"],
        category=row["category"],
        severity=row["severity"],
        filePath=row["file_path"],
        title=row["title"],
        suggestion=row.get("suggestion"),
        lineNumber=row.get("line_number"),
    )
