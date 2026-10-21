import json
import logging
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, Response, status

from app.ai_client import ai_client
from app.config import settings
from app.dev_store import dev_store
from app.github_service import github_service

router = APIRouter(tags=["webhooks"])
logger = logging.getLogger(__name__)


async def _process_pr_webhook(
    repo_full_name: str,
    pull_number: int,
    branch: str,
    commit_sha: str,
    pr_title: str,
    pr_body: str,
) -> None:
    """
    Background worker that executes AST analysis and posts automated PR review
    comments directly back to the GitHub PR.
    """
    try:
        logger.info(f"Analyzing PR #{pull_number} on {repo_full_name} (branch: {branch}, commit: {commit_sha[:7] if commit_sha else 'head'})...")

        # 1. Run static analysis
        analysis_result = await ai_client.analyze_repository(
            repo_url=repo_full_name,
            branch=branch,
        )

        maintainability = int(analysis_result.get("maintainability_score", 88))
        findings = analysis_result.get("findings", [])

        # 2. Synthesize PR Review with AI Service
        review_result = await ai_client.review_pr(
            repo_url=repo_full_name,
            branch=branch,
            pr_title=pr_title,
            pr_description=pr_body,
            maintainability_score=maintainability,
            findings=findings,
        )

        summary = review_result.get("summary", "Automated CodeSense AI Review")
        verdict = review_result.get("verdict", "COMMENT")
        inline_comments = review_result.get("inline_comments", [])
        improvements = review_result.get("suggested_improvements", [])

        # Format markdown review body
        review_body_lines = [
            f"## 🤖 CodeSense AI Automated Review",
            f"**Verdict:** `{verdict}` | **Maintainability Score:** `{maintainability}/100` | **Findings Detected:** `{len(findings)}`\n",
            f"### Summary",
            f"{summary}\n",
        ]

        if improvements:
            review_body_lines.append("### Recommended Improvements")
            for imp in improvements[:5]:
                review_body_lines.append(f"- {imp}")
            review_body_lines.append("")

        formatted_body = "\n".join(review_body_lines)

        # Prepare inline review comments if any
        github_comments = []
        for c in inline_comments[:10]:
            f_path = c.get("file_path") or c.get("path")
            l_num = c.get("line_number") or c.get("line")
            c_text = c.get("comment") or c.get("body")
            patch = c.get("suggested_patch")

            if f_path and l_num and c_text:
                full_c_text = c_text
                if patch:
                    full_c_text += f"\n\n```suggestion\n{patch}\n```"
                github_comments.append({
                    "path": f_path,
                    "line": int(l_num),
                    "body": full_c_text,
                })

        # 3. Post review to GitHub PR
        await github_service.post_pr_review(
            repo_full_name=repo_full_name,
            pull_number=pull_number,
            body=formatted_body,
            event=verdict,
            commit_sha=commit_sha,
            comments=github_comments,
        )

        # Save record in dev_store for persistent dashboard visibility
        dev_store.save_analysis(repo_full_name, {
            "id": uuid4(),
            "repository_id": repo_full_name,
            "branch": branch,
            "commit_sha": commit_sha,
            "maintainability_score": maintainability,
            "technical_debt_hours": int(analysis_result.get("technical_debt_hours", 4)),
            "status": "COMPLETED",
            "progress": 100,
            "error_message": None,
        })

    except Exception as exc:
        logger.error(f"Error processing PR webhook for {repo_full_name} #{pull_number}: {exc}", exc_info=True)


@router.post("/github", status_code=status.HTTP_200_OK)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
) -> dict[str, Any]:
    """
    Handle GitHub webhook events:
    - ping: Webhook handshake
    - pull_request: Automatically triggers CodeSense AST scan & posts PR review comments
    """
    body_bytes = await request.body()
    event = (request.headers.get("x-github-event") or x_github_event or "").lower()
    signature = request.headers.get("x-hub-signature-256") or x_hub_signature_256

    # Validate HMAC signature if secret configured
    if settings.github_webhook_secret:
        is_valid = github_service.verify_webhook_signature(
            payload_bytes=body_bytes,
            signature_header=signature,
            secret=settings.github_webhook_secret,
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid X-Hub-Signature-256 header",
            )

    try:
        payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    # Handle Ping Event
    if event == "ping":
        logger.info("Received GitHub ping webhook.")
        return {"status": "ok", "message": "Pong! CodeSense Webhook is active."}

    # Handle Pull Request Events
    if event == "pull_request":
        action = payload.get("action", "")
        if action in ("opened", "synchronize", "reopened"):
            pr = payload.get("pull_request", {})
            repo = payload.get("repository", {})

            repo_full_name = repo.get("full_name") or repo.get("name")
            pull_number = pr.get("number") or payload.get("number")
            head_ref = pr.get("head", {}).get("ref", "main")
            head_sha = pr.get("head", {}).get("sha", "")
            pr_title = pr.get("title", "")
            pr_body = pr.get("body", "")

            if repo_full_name and pull_number:
                background_tasks.add_task(
                    _process_pr_webhook,
                    repo_full_name=repo_full_name,
                    pull_number=pull_number,
                    branch=head_ref,
                    commit_sha=head_sha,
                    pr_title=pr_title,
                    pr_body=pr_body or "",
                )
                return {
                    "status": "queued",
                    "action": action,
                    "repository": repo_full_name,
                    "pull_number": pull_number,
                    "branch": head_ref,
                }

        return {"status": "ignored", "action": action, "reason": "PR action does not trigger review"}

    return {"status": "ignored", "event": x_github_event}
