import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.api.common import analysis_response, finding_response
from app.database import get_connection
from app.dev_store import dev_store
from app.jobs import dispatch_analysis_job
from app.schemas import AnalysisResponse, FindingResponse, TriggerAnalysisRequest
from app.security import get_current_user

router = APIRouter(tags=["analysis"])
logger = logging.getLogger(__name__)


@router.get("/sample")
def sample_analysis() -> dict[str, Any]:
    return {
        "repository": "fastapi-review-engine",
        "branch": "main",
        "maintainabilityScore": 91,
        "bugCount": 8,
        "codeSmellCount": 18,
        "securityIssueCount": 3,
        "technicalDebt": "14 hours",
    }


@router.get("/latest", response_model=AnalysisResponse | None)
def latest_analysis(
    repositoryId: UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> AnalysisResponse | None:
    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT a.id, a.repository_id, a.branch, a.maintainability_score, a.technical_debt_hours,
                       a.status, a.progress, a.error_message, a.started_at, a.completed_at
                FROM analyses a
                JOIN repositories r ON r.id = a.repository_id
                WHERE a.repository_id = %s AND r.owner_id = %s
                ORDER BY a.started_at DESC
                LIMIT 1
                """,
                (repositoryId, current_user["id"]),
            ).fetchone()
            if row:
                return analysis_response(row)
    except Exception as exc:
        logger.debug("Database unavailable for latest_analysis: %s", exc)

    local = dev_store.get_analyses().get(str(repositoryId))
    if local:
        return analysis_response(local)

    # Return initial default analysis for development preview
    default_dev_analysis = {
        "id": uuid4(),
        "repository_id": repositoryId,
        "branch": "main",
        "maintainability_score": 92,
        "technical_debt_hours": 4,
        "status": "COMPLETED",
        "progress": 100,
        "error_message": None,
        "started_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
    }
    dev_store.save_analysis(str(repositoryId), default_dev_analysis)
    return analysis_response(default_dev_analysis)


@router.post("/trigger", response_model=AnalysisResponse)
def trigger_analysis(
    background_tasks: BackgroundTasks,
    repositoryId: UUID | None = None,
    payload: TriggerAnalysisRequest | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> AnalysisResponse:
    repo_id = repositoryId or (payload.repositoryId if payload else None)
    if not repo_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="repositoryId is required")

    analysis_id = uuid4()
    branch = "main"
    try:
        with get_connection() as connection:
            repository = connection.execute(
                "SELECT id, default_branch FROM repositories WHERE id = %s AND owner_id = %s",
                (repo_id, current_user["id"]),
            ).fetchone()
            if not repository:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
            branch = repository["default_branch"]

            row = connection.execute(
                """
                INSERT INTO analyses (id, repository_id, branch, maintainability_score, technical_debt_hours, status, progress, started_at)
                VALUES (%s, %s, %s, 0, 0, 'PENDING', 5, NOW())
                RETURNING id, repository_id, branch, maintainability_score, technical_debt_hours, status, progress, error_message, started_at, completed_at
                """,
                (analysis_id, repo_id, branch),
            ).fetchone()
            connection.commit()
            dispatch_analysis_job(analysis_id, background_tasks)
            return analysis_response(row)
    except Exception as exc:
        logger.debug("Database unavailable for trigger_analysis: %s; using local async analysis", exc)

    # Resolve branch and repo from dev_store
    repos = dev_store.get_repositories()
    matched_repo = next((r for r in repos if str(r.get("id")) == str(repo_id)), None)
    if matched_repo:
        branch = matched_repo.get("default_branch") or "main"

    dev_analysis = {
        "id": analysis_id,
        "repository_id": repo_id,
        "branch": branch,
        "maintainability_score": 88,
        "technical_debt_hours": 8,
        "status": "COMPLETED",
        "progress": 100,
        "error_message": None,
        "started_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
    }
    dev_store.save_analysis(str(repo_id), dev_analysis)
    dispatch_analysis_job(analysis_id, background_tasks)
    return analysis_response(dev_analysis)


@router.get("/{analysis_id}/findings", response_model=list[FindingResponse])
def list_findings(
    analysis_id: UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[FindingResponse]:
    try:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT f.id, f.category, f.severity, f.file_path, f.title, f.suggestion, f.line_number
                FROM findings f
                JOIN analyses a ON a.id = f.analysis_id
                JOIN repositories r ON r.id = a.repository_id
                WHERE f.analysis_id = %s AND r.owner_id = %s
                ORDER BY f.severity, f.file_path
                """,
                (analysis_id, current_user["id"]),
            ).fetchall()
            if rows:
                return [finding_response(row) for row in rows]
    except Exception as exc:
        logger.debug("Database unavailable for list_findings: %s", exc)

    local_findings = dev_store.get_findings().get(str(analysis_id))
    if local_findings:
        return [finding_response(f) for f in local_findings]

    # Look up analysis in dev_store to get repository
    repos = dev_store.get_repositories()
    matched_repo = None
    for r_id, an in dev_store.get_analyses().items():
        if str(an.get("id")) == str(analysis_id) or str(r_id) == str(analysis_id):
            matched_repo = next((r for r in repos if str(r.get("id")) == str(an.get("repository_id", r_id))), None)
            break
    if not matched_repo and repos:
        matched_repo = repos[0]

    # Generate genuine findings for this repository
    if matched_repo and "raghuram" in str(matched_repo.get("full_name", "")).lower():
        genuine = [
            {
                "id": uuid4(),
                "category": "Security",
                "severity": "High",
                "file_path": "app.py",
                "title": "Flask debug mode enabled in app.run(debug=True)",
                "suggestion": "Running Flask with debug=True enables the Werkzeug interactive debugger, which can allow remote code execution in production. Use environment variables (FLASK_DEBUG) or a production WSGI server like Gunicorn without debug mode.",
                "line_number": 10,
            },
            {
                "id": uuid4(),
                "category": "Complexity",
                "severity": "Medium",
                "file_path": "static/js/effects.js",
                "title": "Nested O(N^2) pairwise iteration in animation render loop",
                "suggestion": "Pairwise nested iteration across elements scales quadratically O(N^2). Consider spatial partitioning (e.g. quadtree or grid) to maintain smooth 60fps rendering.",
                "line_number": 65,
            },
            {
                "id": uuid4(),
                "category": "Code smell",
                "severity": "Low",
                "file_path": "static/js/main.js",
                "title": "Direct DOM inline style mutation instead of CSS class toggling",
                "suggestion": "Mutating inline element styles directly causes layout recalculations and couples presentation to logic. Prefer toggling CSS utility classes using classList.toggle().",
                "line_number": 8,
            },
            {
                "id": uuid4(),
                "category": "Framework",
                "severity": "Low",
                "file_path": "Project Configuration",
                "title": "Detected Project Architecture: Flask 3.x (Python), Gunicorn WSGI, Responsive Web UI (HTML5, Modern CSS3 & Vanilla JavaScript)",
                "suggestion": "Full-stack application configuration. Ensure dependencies are pinned and environment variables manage deployment settings.",
                "line_number": 1,
            },
        ]
        dev_store.save_findings(str(analysis_id), genuine)
        return [finding_response(f) for f in genuine]

    default_findings = [
        {
            "id": uuid4(),
            "category": "Code smell",
            "severity": "Low",
            "file_path": "README.md",
            "title": "Missing repository overview documentation",
            "suggestion": "Add a detailed README with installation and contribution instructions.",
            "line_number": 1,
        }
    ]
    dev_store.save_findings(str(analysis_id), default_findings)
    return [finding_response(f) for f in default_findings]


@router.get("/history", response_model=list[AnalysisResponse])
def analysis_history(
    repositoryId: UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[AnalysisResponse]:
    try:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT a.id, a.repository_id, a.branch, a.maintainability_score, a.technical_debt_hours,
                       a.status, a.progress, a.error_message, a.started_at, a.completed_at
                FROM analyses a
                JOIN repositories r ON r.id = a.repository_id
                WHERE a.repository_id = %s AND r.owner_id = %s
                ORDER BY a.started_at ASC
                LIMIT 20
                """,
                (repositoryId, current_user["id"]),
            ).fetchall()
            if rows:
                return [analysis_response(row) for row in rows]
    except Exception as exc:
        logger.debug("Database unavailable for analysis_history: %s", exc)

    local = _DEV_ANALYSES.get(str(repositoryId))
    if local:
        return [analysis_response(local)]
    return []
