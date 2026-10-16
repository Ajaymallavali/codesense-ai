import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import redis
from fastapi import BackgroundTasks

from app.ai_client import ai_client
from app.config import settings
from app.database import get_connection

logger = logging.getLogger(__name__)

REDIS_QUEUE_KEY = "codesense:queue:analysis"
REDIS_JOB_PREFIX = "codesense:job:"


def get_redis_client() -> redis.Redis | None:
    """Return a connected Redis client, or None if unavailable."""
    try:
        client = redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1.0,
            socket_timeout=2.0,
            decode_responses=True,
        )
        client.ping()
        return client
    except Exception as exc:
        logger.debug(f"Redis is not available: {exc}")
        return None


def check_redis_health() -> dict[str, Any]:
    """Diagnostic check for Redis connectivity."""
    client = get_redis_client()
    if client is None:
        return {"status": "STANDALONE_FALLBACK", "detail": "Redis offline, using FastAPI async background tasks"}
    try:
        info = client.info("server")
        return {"status": "UP", "version": info.get("redis_version", "unknown")}
    except Exception as exc:
        return {"status": "ERROR", "detail": str(exc)}


def _update_redis_job_status(
    analysis_id: str,
    status: str,
    progress: int = 0,
    error: str | None = None,
) -> None:
    """Helper to maintain job status in Redis cache if available."""
    client = get_redis_client()
    if client is None:
        return
    try:
        key = f"{REDIS_JOB_PREFIX}{analysis_id}"
        mapping: dict[str, Any] = {
            "status": status,
            "progress": progress,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if error:
            mapping["error"] = error
        client.hset(key, mapping=mapping)
        client.expire(key, 86400)  # 24h retention
    except Exception as exc:
        logger.warning(f"Failed to update Redis job cache for {analysis_id}: {exc}")


async def process_analysis_job(analysis_id: UUID) -> None:
    """
    Main background job worker function:
    Transitions: PENDING -> SCANNING -> COMPLETED (or FAILED)
    """
    str_id = str(analysis_id)
    logger.info(f"Processing analysis job {str_id}...")

    # Step 1: Read analysis and repo info from DB
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT a.id, a.repository_id, a.branch, a.status,
                   r.name, r.full_name, r.default_branch,
                   u.github_token
            FROM analyses a
            JOIN repositories r ON r.id = a.repository_id
            JOIN users u ON u.id = r.owner_id
            WHERE a.id = %s
            """,
            (analysis_id,),
        ).fetchone()

        if not row:
            logger.error(f"Analysis job {str_id} not found in database.")
            _update_redis_job_status(str_id, "FAILED", error="Analysis record not found")
            return

        # Avoid double-processing if already finished
        if row["status"] in ("COMPLETED", "FAILED"):
            logger.info(f"Analysis job {str_id} is already in state {row['status']}.")
            return

        # Step 2: Transition PENDING -> SCANNING
        connection.execute(
            """
            UPDATE analyses
            SET status = 'SCANNING', progress = 35
            WHERE id = %s
            """,
            (analysis_id,),
        )
        connection.commit()

    _update_redis_job_status(str_id, "SCANNING", progress=35)
    logger.info(f"Analysis {str_id} transitioned to SCANNING.")

    # Step 3: Call AI Service via httpx
    try:
        repo_name = row["full_name"] or row["name"]
        branch = row["branch"] or row["default_branch"] or "main"
        token = row["github_token"]

        result = await ai_client.analyze_repository(
            repo_url=repo_name,
            branch=branch,
            github_token=token,
        )

        maintainability_score = int(result.get("maintainability_score", 85))
        technical_debt_hours = int(result.get("technical_debt_hours", 10))
        raw_findings = result.get("findings", [])

        # Step 4: Transition SCANNING -> COMPLETED and persist findings
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE analyses
                SET maintainability_score = %s,
                    technical_debt_hours = %s,
                    status = 'COMPLETED',
                    progress = 100,
                    completed_at = NOW()
                WHERE id = %s
                """,
                (maintainability_score, technical_debt_hours, analysis_id),
            )

            # Clear old findings for this analysis (idempotent retry)
            connection.execute("DELETE FROM findings WHERE analysis_id = %s", (analysis_id,))

            for f in raw_findings:
                connection.execute(
                    """
                    INSERT INTO findings (id, analysis_id, category, severity, file_path, title, suggestion, line_number)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        uuid4(),
                        analysis_id,
                        f.get("category", "Code Quality"),
                        f.get("severity", "Medium"),
                        f.get("file") or f.get("file_path") or "Unknown",
                        f.get("title", "Detected code finding"),
                        f.get("suggestion", ""),
                        f.get("line_number") or f.get("lineNumber") or 1,
                    ),
                )
            connection.commit()

        _update_redis_job_status(str_id, "COMPLETED", progress=100)
        logger.info(f"Analysis job {str_id} successfully COMPLETED with {len(raw_findings)} findings.")

    except Exception as exc:
        err_msg = str(exc)
        logger.error(f"Analysis job {str_id} FAILED: {err_msg}")
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE analyses
                SET status = 'FAILED',
                    error_message = %s,
                    completed_at = NOW()
                WHERE id = %s
                """,
                (err_msg, analysis_id),
            )
            connection.commit()

        _update_redis_job_status(str_id, "FAILED", error=err_msg)


def dispatch_analysis_job(analysis_id: UUID, background_tasks: BackgroundTasks) -> None:
    """
    Queue the analysis job in Redis if available, and schedule async execution
    using FastAPI's BackgroundTasks worker.
    """
    str_id = str(analysis_id)
    client = get_redis_client()
    if client is not None:
        try:
            client.lpush(REDIS_QUEUE_KEY, json.dumps({"analysis_id": str_id}))
            _update_redis_job_status(str_id, "PENDING", progress=5)
            logger.info(f"Dispatched analysis {str_id} to Redis queue: {REDIS_QUEUE_KEY}")
        except Exception as exc:
            logger.warning(f"Could not push to Redis queue: {exc}")

    # Schedule async background task
    background_tasks.add_task(process_analysis_job, analysis_id)
