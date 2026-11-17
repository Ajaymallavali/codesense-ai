from datetime import datetime, timezone
import json
import logging
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.ai_client import ai_client
from app.config import settings
from app.database import get_connection
from app.dev_store import dev_store
from app.schemas import (
    AiChatRequest,
    AiExplainRequest,
    PrInlineComment,
    PrReviewRequest,
    PrReviewResponse,
)
from app.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ai"])


@router.post("/chat")
async def ai_chat(
    payload: AiChatRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    query_text = (payload.query or payload.message or "").strip()
    if not query_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query message cannot be empty")

    user_id_str = str(current_user["id"])
    repo_target = "Ajaymallavali/Raghuram_portfolio"
    branch = "main"
    token = current_user.get("github_token")
    findings_list: list[dict[str, Any]] = []
    maintainability_score: int | None = None
    technical_debt_hours: int | None = None
    target_repo_id = payload.repositoryId

    # 1. If repositoryId not explicitly passed, pick user's active repository
    if not target_repo_id:
        try:
            with get_connection() as connection:
                user_repo = connection.execute(
                    "SELECT id FROM repositories WHERE owner_id = %s ORDER BY imported_at DESC LIMIT 1",
                    (current_user["id"],),
                ).fetchone()
                if user_repo:
                    target_repo_id = user_repo["id"]
        except Exception:
            pass

        if not target_repo_id:
            dev_repos = dev_store.get_repositories()
            matched = next((r for r in dev_repos if not r.get("owner_id") or str(r.get("owner_id")) == user_id_str), None)
            if matched:
                target_repo_id = matched.get("id")

    # 2. Look up repository details and findings
    if target_repo_id:
        try:
            with get_connection() as connection:
                repo = connection.execute(
                    "SELECT name, full_name, default_branch FROM repositories WHERE id = %s AND owner_id = %s",
                    (target_repo_id, current_user["id"]),
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
                        (target_repo_id,),
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
        except Exception as exc:
            logger.debug("Database unavailable for ai_chat: %s", exc)

        # Fallback to dev_store if PostgreSQL returned nothing or is offline
        if not findings_list:
            repos = dev_store.get_repositories()
            matched_repo = next(
                (r for r in repos if str(r.get("id")) == str(target_repo_id) or r.get("full_name") == str(target_repo_id) or r.get("name") == str(target_repo_id)),
                None,
            )
            if not matched_repo and repos:
                matched_repo = next((r for r in repos if str(r.get("owner_id")) == user_id_str), repos[0])
            if matched_repo:
                repo_target = matched_repo.get("full_name") or matched_repo.get("name") or repo_target
                branch = matched_repo.get("default_branch") or branch
                local_analysis = dev_store.get_analyses().get(str(matched_repo.get("id")))
                if local_analysis:
                    maintainability_score = local_analysis.get("maintainability_score", 92)
                    technical_debt_hours = local_analysis.get("technical_debt_hours", 4)
                    analysis_id_str = str(local_analysis.get("id", ""))
                    local_findings = dev_store.get_findings().get(analysis_id_str)
                    if not local_findings:
                        local_findings = dev_store.get_findings().get(str(matched_repo.get("id", ""))) or []
                    findings_list = [
                        {
                            "category": f.get("category", "Code smell"),
                            "severity": f.get("severity", "Medium"),
                            "file": f.get("file_path") or f.get("file", "unknown"),
                            "title": f.get("title", ""),
                            "suggestion": f.get("suggestion", ""),
                            "line_number": f.get("line_number", 1),
                        }
                        for f in (local_findings or [])
                    ]

    # Note: Static analysis is processed asynchronously on import or via /analysis/trigger.
    # Chat runs immediately against existing findings and RAG vectors without blocking on git clone.

    # Multi-turn conversational memory: preserve recent context for senior engineer continuity
    history_turns: list[dict[str, Any]] = []
    incoming_msgs = payload.messages or payload.conversationHistory
    if incoming_msgs:
        for m in incoming_msgs[-8:]:
            c = m.get("content") or m.get("text") or ""
            if c:
                history_turns.append({"role": m.get("role", "user"), "content": c})
    elif payload.conversationId:
        try:
            raw_msgs = dev_store.get_conversation_messages(str(payload.conversationId))
            if raw_msgs:
                for m in raw_msgs[-8:]:
                    c = m.get("content") or m.get("text") or ""
                    if c:
                        history_turns.append({"role": m.get("role", "user"), "content": c})
        except Exception:
            pass

    chat_res = await ai_client.chat(
        repo_url=repo_target,
        branch=payload.branch or branch,
        query=query_text,
        maintainability_score=maintainability_score,
        technical_debt_hours=technical_debt_hours,
        findings=findings_list,
        github_token=token,
        conversation_id=str(payload.conversationId) if payload.conversationId else None,
        commit_sha=payload.commitSha,
        conversation_history=history_turns,
    )
    response_text = chat_res.get("response", "")
    citations = chat_res.get("citations", [])
    conv_id = chat_res.get("conversation_id") or str(payload.conversationId or uuid.uuid4())

    # Persist conversation and messages to PostgreSQL if available, and dev_store
    citations_json = json.dumps(citations) if citations else None
    repo_uuid = target_repo_id if target_repo_id else None

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO conversations (id, repository_id, user_id, title, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (id) DO UPDATE SET updated_at = NOW()
                """,
                (conv_id, repo_uuid, current_user["id"], query_text[:80]),
            )
            connection.execute(
                """
                INSERT INTO conversation_messages (id, conversation_id, role, content, citations)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (uuid.uuid4(), conv_id, "user", query_text, None),
            )
            connection.execute(
                """
                INSERT INTO conversation_messages (id, conversation_id, role, content, citations)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (uuid.uuid4(), conv_id, "assistant", response_text, citations_json),
            )
            connection.commit()
    except Exception as db_err:
        logger.debug("Database unavailable to save conversation %s: %s", conv_id, db_err)

    try:
        repo_identifiers = set()
        if repo_uuid:
            repo_identifiers.add(str(repo_uuid))
        if payload.repositoryId:
            repo_identifiers.add(str(payload.repositoryId))
        if matched_repo:
            if matched_repo.get("id"):
                repo_identifiers.add(str(matched_repo["id"]))
            if matched_repo.get("name"):
                repo_identifiers.add(str(matched_repo["name"]))
            if matched_repo.get("full_name"):
                repo_identifiers.add(str(matched_repo["full_name"]))

        u_entry = {
            "role": "user",
            "content": query_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        a_entry = {
            "role": "assistant",
            "content": response_text,
            "citations": citations,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        dev_store.save_conversation_message(conv_id, u_entry, user_id=user_id_str)
        dev_store.save_conversation_message(conv_id, a_entry, user_id=user_id_str)
        for r_id in repo_identifiers:
            dev_store.index_repo_conversation(r_id, conv_id, user_id=user_id_str)
    except Exception as conv_err:
        logger.debug("Failed saving dev_store conversation history: %s", conv_err)

    return {
        "response": response_text,
        "answer": response_text,
        "citations": citations,
        "conversationId": conv_id,
        "provider": chat_res.get("provider", "cloudflare"),
    }


@router.get("/conversations/latest")
def get_latest_conversation(
    repositoryId: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Compulsory repository conversation retrieval: fetches most recent session for active repository."""
    if not repositoryId:
        return {"conversationId": None, "messages": []}

    conv_id = None
    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT id FROM conversations
                WHERE repository_id = %s AND user_id = %s
                ORDER BY updated_at DESC LIMIT 1
                """,
                (repositoryId, current_user["id"]),
            ).fetchone()
            if row:
                conv_id = str(row["id"])
    except Exception:
        pass

    if not conv_id:
        conv_id = dev_store.get_latest_conversation_for_repo(str(repositoryId), user_id=str(current_user["id"]))

    if not conv_id:
        return {"conversationId": None, "messages": []}

    return get_conversation_history(conv_id, current_user)


@router.get("/conversations/{conversation_id}")
def get_conversation_history(
    conversation_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    # 1. Attempt retrieval from PostgreSQL
    try:
        with get_connection() as connection:
            conv = connection.execute(
                "SELECT user_id FROM conversations WHERE id = %s",
                (conversation_id,),
            ).fetchone()
            if conv:
                if str(conv["user_id"]) != str(current_user["id"]) and settings.environment != "development":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to conversation",
                    )
                msg_rows = connection.execute(
                    """
                    SELECT role, content, citations, created_at
                    FROM conversation_messages
                    WHERE conversation_id = %s
                    ORDER BY created_at ASC
                    """,
                    (conversation_id,),
                ).fetchall()
                parsed_messages = []
                for m in msg_rows:
                    entry = {
                        "role": m["role"],
                        "content": m["content"],
                        "timestamp": m["created_at"].isoformat() if m.get("created_at") else "",
                    }
                    if m.get("citations"):
                        try:
                            entry["citations"] = json.loads(m["citations"]) if isinstance(m["citations"], str) else m["citations"]
                        except Exception:
                            entry["citations"] = []
                    parsed_messages.append(entry)
                return {
                    "conversationId": conversation_id,
                    "messages": parsed_messages,
                }
    except HTTPException:
        raise
    except Exception as db_err:
        logger.debug("Database unavailable for get_conversation_history: %s", db_err)

    # 2. Fall back to dev_store
    owner_id = dev_store.get_conversation_owner(conversation_id)
    if owner_id and owner_id != str(current_user["id"]) and settings.environment != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to conversation",
        )
    messages = dev_store.get_conversation_messages(conversation_id)
    return {
        "conversationId": conversation_id,
        "messages": messages,
    }


@router.post("/explain")
async def ai_explain(
    payload: AiExplainRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    repo_target = "Ajaymallavali/Raghuram_portfolio"
    branch = "main"
    token = current_user.get("github_token")
    finding_dict: dict[str, Any] = {}

    if payload.findingId:
        try:
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
        except Exception as exc:
            logger.debug("Database unavailable for ai_explain: %s", exc)

        # Fallback to dev_store
        if not finding_dict:
            for analysis_id, f_list in dev_store.get_findings().items():
                for f in f_list:
                    if str(f.get("id")) == str(payload.findingId):
                        finding_dict = {
                            "category": f.get("category", "Code Review"),
                            "severity": f.get("severity", "Medium"),
                            "file_path": f.get("file_path") or f.get("file", "unknown"),
                            "title": f.get("title", ""),
                            "suggestion": f.get("suggestion", ""),
                            "line_number": f.get("line_number", 1),
                        }
                        break
                if finding_dict:
                    break

    if not finding_dict:
        finding_dict = {
            "category": "Security",
            "severity": "High",
            "file_path": "app.py",
            "title": "Flask debug mode enabled in app.run(debug=True)",
            "suggestion": "Set debug mode from environment variables (FLASK_DEBUG) and run using Gunicorn in production.",
            "line_number": 10,
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
    repo_target = payload.repositoryUrl or "Ajaymallavali/Raghuram_portfolio"
    branch = payload.branch or "main"
    token = current_user.get("github_token")
    findings_list: list[dict[str, Any]] = []
    maintainability_score: int | None = None
    technical_debt_hours: int | None = None

    if payload.repositoryId:
        try:
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
        except Exception as exc:
            logger.debug("Database unavailable for ai_review_pr: %s", exc)

        # Fallback to dev_store
        if not findings_list:
            repos = dev_store.get_repositories()
            matched_repo = next((r for r in repos if str(r.get("id")) == str(payload.repositoryId)), None)
            if not matched_repo and repos:
                matched_repo = repos[0]
            if matched_repo:
                repo_target = payload.repositoryUrl or matched_repo.get("full_name") or matched_repo.get("name") or repo_target
                branch = payload.branch or matched_repo.get("default_branch") or branch
                local_analysis = dev_store.get_analyses().get(str(matched_repo.get("id")))
                if local_analysis:
                    maintainability_score = local_analysis.get("maintainability_score", 92)
                    technical_debt_hours = local_analysis.get("technical_debt_hours", 4)
                    local_findings = dev_store.get_findings().get(str(local_analysis.get("id", ""))) or []
                    findings_list = [
                        {
                            "category": f.get("category", "Code smell"),
                            "severity": f.get("severity", "Medium"),
                            "file": f.get("file_path") or f.get("file", "unknown"),
                            "title": f.get("title", ""),
                            "suggestion": f.get("suggestion", ""),
                            "line_number": f.get("line_number", 1),
                        }
                        for f in local_findings
                    ]

        # If findings are still empty, run on-demand scan via AI Service
        if not findings_list and repo_target and not repo_target.startswith("example/"):
            try:
                scanned = await ai_client.analyze_repository(repo_target, branch, token)
                maintainability_score = scanned.get("maintainability_score", 92)
                technical_debt_hours = scanned.get("technical_debt_hours", 4)
                findings_list = [
                    {
                        "category": f.get("category", "Code smell"),
                        "severity": f.get("severity", "Medium"),
                        "file": f.get("file") or f.get("file_path", "unknown"),
                        "title": f.get("title", ""),
                        "suggestion": f.get("suggestion", ""),
                        "line_number": f.get("line_number", 1),
                    }
                    for f in scanned.get("findings", [])
                ]
            except Exception as scan_err:
                logger.warning("On-demand scan for ai_review_pr failed: %s", scan_err)

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
