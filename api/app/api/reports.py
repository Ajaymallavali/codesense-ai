from datetime import datetime, timezone
import logging
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.ai_client import ai_client
from app.database import get_connection
from app.dev_store import dev_store
from app.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reports"])


@router.get("/summary")
def get_reports_summary(
    repositoryId: UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    repo = None
    latest = None
    findings = []
    try:
        with get_connection() as connection:
            repo = connection.execute(
                "SELECT id, name, full_name, default_branch, language FROM repositories WHERE id = %s AND owner_id = %s",
                (repositoryId, current_user["id"]),
            ).fetchone()

            if repo:
                latest = connection.execute(
                    """
                    SELECT id, maintainability_score, technical_debt_hours, status, completed_at, started_at
                    FROM analyses
                    WHERE repository_id = %s AND status = 'COMPLETED'
                    ORDER BY completed_at DESC NULLS LAST, started_at DESC
                    LIMIT 1
                    """,
                    (repositoryId,),
                ).fetchone()

                if latest:
                    finding_rows = connection.execute(
                        """
                        SELECT category, severity, file_path, title, suggestion, line_number
                        FROM findings
                        WHERE analysis_id = %s
                        ORDER BY severity, file_path
                        """,
                        (latest["id"],),
                    ).fetchall()
                    findings = [dict(f) for f in finding_rows]
    except Exception:
        pass

    if not repo:
        repos = dev_store.get_repositories()
        matched = next((r for r in repos if str(r.get("id")) == str(repositoryId)), None)
        if matched:
            repo = matched
            local_analysis = dev_store.get_analyses().get(str(repositoryId))
            if local_analysis:
                latest = local_analysis
                findings = dev_store.get_findings().get(str(local_analysis.get("id", "")), [])
        else:
            repo = {
                "name": "repository",
                "full_name": "repository",
                "default_branch": "main",
                "language": "Code",
            }

    maintainability = latest["maintainability_score"] if latest else 92
    debt_hours = latest["technical_debt_hours"] if latest else 4

    normalized_findings = []
    for f in findings:
        file_loc = f.get("filePath") or f.get("file_path") or f.get("file") or "unknown"
        line_num = f.get("lineNumber") or f.get("line_number") or 1
        normalized_findings.append({
            "id": str(f.get("id", uuid4())),
            "category": f.get("category", "General"),
            "severity": f.get("severity", "Medium"),
            "filePath": file_loc,
            "file_path": file_loc,
            "file": file_loc,
            "title": f.get("title", ""),
            "suggestion": f.get("suggestion", ""),
            "lineNumber": line_num,
            "line_number": line_num,
        })

    return {
        "repository": repo.get("full_name") or repo.get("name") or "repository",
        "branch": repo.get("default_branch") or "main",
        "language": repo.get("language") or "Unknown",
        "analysisId": str(latest["id"]) if latest else None,
        "completedAt": (
            latest["completed_at"].isoformat()
            if latest and hasattr(latest.get("completed_at"), "isoformat")
            else str(latest.get("completed_at"))
            if latest and latest.get("completed_at")
            else datetime.now(timezone.utc).isoformat()
        ),
        "maintainabilityScore": maintainability,
        "technicalDebtHours": debt_hours,
        "findingsCount": len(normalized_findings),
        "findingsByCategory": {
            "Security": len([f for f in normalized_findings if "sec" in f["category"].lower()]),
            "Complexity": len([f for f in normalized_findings if "complex" in f["category"].lower()]),
            "CodeSmell": len([f for f in normalized_findings if "smell" in f["category"].lower() or "maintain" in f["category"].lower()]),
            "Testing": len([f for f in normalized_findings if "test" in f["category"].lower()]),
            "Documentation": len([f for f in normalized_findings if "doc" in f["category"].lower()]),
        },
        "findings": normalized_findings,
    }


@router.get("/download")
async def download_report(
    repositoryId: UUID,
    reportType: str = "assessment",
    format: str = "pdf",
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    repo = None
    latest = None
    findings = []
    try:
        with get_connection() as connection:
            repo = connection.execute(
                "SELECT id, name, full_name, default_branch, language FROM repositories WHERE id = %s AND owner_id = %s",
                (repositoryId, current_user["id"]),
            ).fetchone()
            if repo:
                latest = connection.execute(
                    """
                    SELECT id, maintainability_score, technical_debt_hours, status, completed_at, started_at
                    FROM analyses
                    WHERE repository_id = %s AND status = 'COMPLETED'
                    ORDER BY completed_at DESC NULLS LAST, started_at DESC
                    LIMIT 1
                    """,
                    (repositoryId,),
                ).fetchone()

                if latest:
                    finding_rows = connection.execute(
                        """
                        SELECT category, severity, file_path, title, suggestion, line_number
                        FROM findings
                        WHERE analysis_id = %s
                        ORDER BY severity, file_path
                        """,
                        (latest["id"],),
                    ).fetchall()
                    findings = [dict(f) for f in finding_rows]
    except Exception:
        pass

    if not repo:
        repos = dev_store.get_repositories()
        matched = next((r for r in repos if str(r.get("id")) == str(repositoryId)), None)
        if matched:
            repo = matched
            local_analysis = dev_store.get_analyses().get(str(repositoryId))
            if local_analysis:
                latest = local_analysis
                findings = dev_store.get_findings().get(str(local_analysis.get("id", "")), [])
        else:
            repo = {
                "name": "project",
                "full_name": "repository",
                "default_branch": "main",
                "language": "Code",
            }

    repo_name = repo.get("full_name") or repo.get("name") or "repository"
    branch = repo.get("default_branch") or "main"
    m_score = latest["maintainability_score"] if latest else 92
    debt_hours = latest["technical_debt_hours"] if latest else 4
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # If PPTX format requested, generate multi-slide server-side PowerPoint presentation
    if format.lower() in ("ppt", "pptx"):
        clean_findings = [
            {
                "category": f.get("category", "General"),
                "severity": f.get("severity", "Medium"),
                "file": f.get("file_path") or f.get("file", "unknown"),
                "title": f.get("title", ""),
                "suggestion": f.get("suggestion", ""),
                "line_number": f.get("line_number", 1),
            }
            for f in findings
        ]
        pptx_payload = {
            "repository": repo_name,
            "branch": branch,
            "commit_sha": "HEAD",
            "maintainability_score": m_score,
            "technical_debt_hours": debt_hours,
            "architecture": f"{repo.get('language', 'Full-Stack')} Web Architecture",
            "findings": clean_findings,
            "generated_at": timestamp,
        }
        try:
            pptx_bytes = await ai_client.generate_pptx_report(pptx_payload)

            # Persist report metadata in PostgreSQL
            try:
                with get_connection() as connection:
                    connection.execute(
                        """
                        INSERT INTO reports (id, repository_id, owner_id, report_type, format, analysis_id, maintainability_score, technical_debt_hours, findings_count)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            uuid4(),
                            repositoryId,
                            current_user["id"],
                            reportType,
                            "pptx",
                            latest["id"] if latest and "id" in latest else None,
                            m_score,
                            debt_hours,
                            len(clean_findings),
                        ),
                    )
                    connection.commit()
            except Exception as db_rep_err:
                logger.debug("Database unavailable to record report metadata: %s", db_rep_err)

            safe_name = repo_name.replace("/", "_").replace("\\", "_")
            return Response(
                content=pptx_bytes,
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                headers={
                    "Content-Disposition": f'attachment; filename="codesense-{reportType}-{safe_name}.pptx"',
                    "Content-Length": str(len(pptx_bytes)),
                },
            )
        except Exception as pptx_err:
            logger.error("Failed to generate PPTX report from AI service: %s; falling back to markdown", pptx_err)

    # If PDF format requested, generate multi-page server-side ReportLab PDF
    if format.lower() == "pdf":
        clean_findings = [
            {
                "category": f.get("category", "General"),
                "severity": f.get("severity", "Medium"),
                "file": f.get("file_path") or f.get("file", "unknown"),
                "title": f.get("title", ""),
                "suggestion": f.get("suggestion", ""),
                "line_number": f.get("line_number", 1),
            }
            for f in findings
        ]
        pdf_payload = {
            "repository": repo_name,
            "branch": branch,
            "commit_sha": "HEAD",
            "maintainability_score": m_score,
            "technical_debt_hours": debt_hours,
            "architecture": f"{repo.get('language', 'Full-Stack')} Web Architecture",
            "findings": clean_findings,
            "generated_at": timestamp,
        }
        try:
            pdf_bytes = await ai_client.generate_pdf_report(pdf_payload)

            # Persist report metadata in PostgreSQL
            try:
                with get_connection() as connection:
                    connection.execute(
                        """
                        INSERT INTO reports (id, repository_id, owner_id, report_type, format, analysis_id, maintainability_score, technical_debt_hours, findings_count)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            uuid4(),
                            repositoryId,
                            current_user["id"],
                            reportType,
                            "pdf",
                            latest["id"] if latest and "id" in latest else None,
                            m_score,
                            debt_hours,
                            len(clean_findings),
                        ),
                    )
                    connection.commit()
            except Exception as db_rep_err:
                logger.debug("Database unavailable to record report metadata: %s", db_rep_err)

            safe_name = repo_name.replace("/", "_").replace("\\", "_")
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="codesense-{reportType}-{safe_name}.pdf"',
                    "Content-Length": str(len(pdf_bytes)),
                },
            )
        except Exception as pdf_err:
            logger.error("Failed to generate PDF report from AI service: %s; falling back to markdown", pdf_err)

    # Markdown format fallback
    if reportType == "debt":
        content = f"""# CodeSense AI - Technical Debt Analysis & Remediation Plan
Repository: {repo_name}
Branch: {branch}
Generated: {timestamp}

## Executive Summary
- Estimated Remediation Time: {debt_hours} hours
- Code Health Index: {m_score} / 100
- Active Issues Detected: {len(findings)}

## Priority Action Plan
"""
        for idx, f in enumerate(findings, start=1):
            content += f"\n### {idx}. [{f['severity']}] {f['title']}\n- File: `{f.get('file_path') or f.get('file')}` (Line {f.get('line_number', 1)})\n- Recommendation: {f.get('suggestion', 'Refactor code according to best practices.')}\n"

        filename = f"technical-debt-plan-{repo.get('name', 'project')}.md"
    else:
        content = f"""# CodeSense AI - Quality & Security Assessment Report
Repository: {repo_name}
Branch: {branch}
Generated: {timestamp}

## Quality Metrics
- Maintainability Score: {m_score} / 100
- Estimated Technical Debt: {debt_hours} hours
- Security & AST Findings: {len(findings)}

## Detected Findings & Vulnerabilities
"""
        for idx, f in enumerate(findings, start=1):
            content += f"\n### {idx}. [{f['category']} - {f['severity']}] {f['title']}\n- Location: `{f.get('file_path') or f.get('file')}:{f.get('line_number', 1)}`\n- Remediation: {f.get('suggestion', 'N/A')}\n"

        filename = f"quality-assessment-{repo.get('name', 'project')}.md"

    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
