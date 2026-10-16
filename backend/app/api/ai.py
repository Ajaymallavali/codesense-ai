from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.ai_client import ai_client
from app.database import get_connection
from app.schemas import (
    AiChatRequest,
    AiExplainRequest,
    PrInlineComment,
    PrReviewRequest,
    PrReviewResponse,
)
from app.security import get_current_user

router = APIRouter(tags=["ai"])


@router.post("/chat")
async def ai_chat(
    payload: AiChatRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    query_text = (payload.query or payload.message or "").strip()
    if not query_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query message cannot be empty")

    repo_target = "example/fastapi-review-engine"
    branch = "main"
    token = current_user.get("github_token")
    findings_list: list[dict[str, Any]] = []
    maintainability_score: int | None = None
    technical_debt_hours: int | None = None

    if payload.repositoryId:
        with get_connection() as connection:
            repo = connection.execute(
                "SELECT name, full_name, default_branch FROM repositories WHERE id = %s AND owner_id = %s",
                (payload.repositoryId, current_user["id"]),
            ).fetchone()
            if repo:
                repo_target = repo["full_name"] or repo["name"]
                branch = repo["default_branch"] or "main"
                latest_analysis = connection.execute(
                    """
                    SELECT id, maintainability_score, technical_debt_hours
                    FROM analyses
                    WHERE repository_id = %s AND status = 'COMPLETED'
                    ORDER BY completed_at DESC NULLS LAST, started_at DESC
                    LIMIT 1
                    """,
                    (payload.repositoryId,),
                ).fetchone()
                if latest_analysis:
                    maintainability_score = latest_analysis["maintainability_score"]
                    technical_debt_hours = latest_analysis["technical_debt_hours"]
                    finding_rows = connection.execute(
                        """
                        SELECT category, severity, file_path, title, suggestion, line_number
                        FROM findings
                        WHERE analysis_id = %s
                        ORDER BY line_number ASC
                        LIMIT 30
                        """,
                        (latest_analysis["id"],),
                    ).fetchall()
                    findings_list = [
                        {
                            "category": f["category"],
                            "severity": f["severity"],
                            "file": f["file_path"],
                            "title": f["title"],
                            "suggestion": f["suggestion"] or "",
                            "line_number": f["line_number"] or 1,
                        }
                        for f in finding_rows
                    ]

    response_text = await ai_client.chat(
        repo_url=repo_target,
        branch=branch,
        query=query_text,
        maintainability_score=maintainability_score,
        technical_debt_hours=technical_debt_hours,
        findings=findings_list,
        github_token=token,
    )
    return {
        "response": response_text,
        "answer": response_text,
    }


@router.post("/explain")
async def ai_explain(
    payload: AiExplainRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    repo_target = "example/fastapi-review-engine"
    branch = "main"
    token = current_user.get("github_token")
    finding_dict: dict[str, Any] = {}

    if payload.findingId:
        with get_connection() as connection:
            finding_row = connection.execute(
                """
                SELECT f.category, f.severity, f.file_path, f.title, f.suggestion, f.line_number,
                       r.name, r.full_name, r.default_branch
                FROM findings f
                JOIN analyses a ON a.id = f.analysis_id
                JOIN repositories r ON r.id = a.repository_id
                WHERE f.id = %s AND r.owner_id = %s
                """,
                (payload.findingId, current_user["id"]),
            ).fetchone()
            if finding_row:
                finding_dict = {
                    "category": finding_row["category"],
                    "severity": finding_row["severity"],
                    "file_path": finding_row["file_path"],
                    "title": finding_row["title"],
                    "suggestion": finding_row["suggestion"] or "",
                    "line_number": finding_row["line_number"] or 1,
                }
                repo_target = finding_row["full_name"] or finding_row["name"]
                branch = finding_row["default_branch"] or "main"

    if not finding_dict:
        finding_dict = {
            "category": "Code Review",
            "severity": "Medium",
            "file_path": (payload.code[:40] if payload.code else "Snippet"),
            "title": "Code analysis snippet",
            "suggestion": payload.code or "Review code snippet",
            "line_number": 1,
        }

    return await ai_client.explain(
        repo_url=repo_target,
        branch=branch,
        finding=finding_dict,
        code_snippet=payload.code,
        github_token=token,
    )


@router.post("/review/pr", response_model=PrReviewResponse)
async def ai_review_pr(
    payload: PrReviewRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> PrReviewResponse:
    repo_target = payload.repositoryUrl or "example/fastapi-review-engine"
    branch = payload.branch or "main"
    token = current_user.get("github_token")
    findings_list: list[dict[str, Any]] = []
    maintainability_score: int | None = None
    technical_debt_hours: int | None = None

    if payload.repositoryId:
        with get_connection() as connection:
            repo = connection.execute(
                "SELECT name, full_name, default_branch FROM repositories WHERE id = %s AND owner_id = %s",
                (payload.repositoryId, current_user["id"]),
            ).fetchone()
            if repo:
                repo_target = repo["full_name"] or repo["name"]
                branch = payload.branch or repo["default_branch"] or "main"
                latest_analysis = connection.execute(
                    """
                    SELECT id, maintainability_score, technical_debt_hours
                    FROM analyses
                    WHERE repository_id = %s AND status = 'COMPLETED'
                    ORDER BY completed_at DESC NULLS LAST, started_at DESC
                    LIMIT 1
                    """,
                    (payload.repositoryId,),
                ).fetchone()
                if latest_analysis:
                    maintainability_score = latest_analysis["maintainability_score"]
                    technical_debt_hours = latest_analysis["technical_debt_hours"]
                    finding_rows = connection.execute(
                        """
                        SELECT category, severity, file_path, title, suggestion, line_number
                        FROM findings
                        WHERE analysis_id = %s
                        ORDER BY line_number ASC
                        LIMIT 30
                        """,
                        (latest_analysis["id"],),
                    ).fetchall()
                    findings_list = [
                        {
                            "category": f["category"],
                            "severity": f["severity"],
                            "file": f["file_path"],
                            "title": f["title"],
                            "suggestion": f["suggestion"] or "",
                            "line_number": f["line_number"] or 1,
                        }
                        for f in finding_rows
                    ]

    result = await ai_client.review_pr(
        repo_url=repo_target,
        branch=branch,
        base_branch=payload.baseBranch or "main",
        pr_title=payload.prTitle or f"PR on {repo_target}",
        pr_description=payload.prDescription or "Automated pull request review request",
        diff_or_code=payload.diff,
        findings=findings_list,
        maintainability_score=maintainability_score,
        technical_debt_hours=technical_debt_hours,
        github_token=token,
    )

    raw_inline = result.get("inline_comments") or []
    inline_comments = [
        PrInlineComment(
            filePath=c.get("file_path") or c.get("filePath") or "general",
            lineNumber=c.get("line_number") or c.get("lineNumber"),
            severity=c.get("severity") or "Medium",
            comment=c.get("comment") or "",
            suggestedPatch=c.get("suggested_patch") or c.get("suggestedPatch"),
        )
        for c in raw_inline
    ]

    return PrReviewResponse(
        summary=result.get("summary") or "Automated PR review generated.",
        verdict=result.get("verdict") or "COMMENT",
        riskLevel=result.get("risk_level") or result.get("riskLevel") or "Medium",
        inlineComments=inline_comments,
        suggestedImprovements=result.get("suggested_improvements") or result.get("suggestedImprovements") or [],
    )
