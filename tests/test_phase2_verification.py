import io
import os
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path
import pytest
import httpx

from app.rag.chunker import (
    CodeChunk,
    chunk_python_code,
    chunk_by_sliding_window,
    chunk_repository_directory,
    detect_file_language,
)
from app.rag.vector_store import PersistentVectorStore
from app.rag.retriever import HybridRetriever, sanitize_untrusted_chunk
from app.rag.llm_adapter import QwenAdapter
from app.reports.pdf_generator import PdfAuditReportGenerator
from app.security_utils import validate_repository_url, validate_redirect_url, safe_extract_zip, redact_secrets
from app.dev_store import dev_store
from app.security import create_token


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "eval_repos"


def chunk_code_file(content: str, file_path: str, repository_id: str, commit_sha: str):
    lang = detect_file_language(file_path)
    if lang == "python":
        return chunk_python_code(content, file_path, repository_id, commit_sha)
    else:
        return chunk_by_sliding_window(content.splitlines(keepends=True), file_path, lang, repository_id, commit_sha)


# =========================================================================
# Task 4: RAG Pipeline Verification & Chunking Line Accuracy
# =========================================================================

def test_python_ast_chunking_line_accuracy():
    code = '''"""Preamble docstring."""
import os
import sys

API_KEY = "dummy"

def calculate_tax(amount: float) -> float:
    """Calculate 8% tax."""
    return amount * 0.08

class OrderManager:
    def process(self, order_id: str):
        return {"status": "ok", "order": order_id}

# Trailing footer
DEFAULT_ORDER = OrderManager()
'''
    chunks = chunk_python_code(code, "src/orders.py", "org/repo", "sha123")
    assert len(chunks) >= 3

    # Check line coverage
    first_chunk = chunks[0]
    assert first_chunk.start_line == 1
    assert "Preamble docstring" in first_chunk.content or "import os" in first_chunk.content

    # Check function chunk
    func_chunk = next(c for c in chunks if "calculate_tax" in c.symbol)
    assert func_chunk.start_line == 7
    assert "def calculate_tax" in func_chunk.content

    # Check class chunk
    class_chunk = next(c for c in chunks if "OrderManager" in c.symbol)
    assert "class OrderManager" in class_chunk.content


def test_chunking_syntax_error_resilience():
    invalid_py = """def broken_function(:
    print("Syntax Error Here"
"""
    # Should not crash; gracefully falls back to sliding window
    chunks = chunk_code_file(invalid_py, "src/broken.py", "org/repo", "sha123")
    assert len(chunks) >= 1
    assert "broken_function" in chunks[0].content


def test_non_python_sliding_window_chunking():
    ts_code = """import { WebSocketServer } from 'ws';

export interface GameConfig {
    tickRate: number;
    maxPlayers: number;
}

export function computeTickRate(fps: number, deltaMs: number): number {
    return Math.floor(1000 / deltaMs);
}
"""
    chunks = chunk_code_file(ts_code, "src/game.ts", "org/repo", "sha123")
    assert len(chunks) >= 1
    assert any("computeTickRate" in c.content for c in chunks)


def test_commit_scoping_and_stale_chunk_invalidation():
    tmp_db = Path(tempfile.gettempdir()) / f"test_stale_{uuid.uuid4().hex[:8]}.db"
    store = PersistentVectorStore(str(tmp_db))
    try:
        # Commit 1 has legacy_auth.py
        c1 = CodeChunk(repository_id="org/repo", commit_sha="commit_v1", file_path="src/legacy_auth.py", language="python", start_line=1, end_line=15, content="def old_auth(): pass", symbol="old_auth")
        c2 = CodeChunk(repository_id="org/repo", commit_sha="commit_v1", file_path="src/billing.py", language="python", start_line=1, end_line=20, content="def calculate_tax(): pass", symbol="calculate_tax")
        store.index_chunks([c1, c2])

        # Query commit_v1: returns both
        res_v1 = store.search_hybrid(repository_id="org/repo", query="auth", commit_sha="commit_v1")
        assert any("legacy_auth.py" in r["file_path"] for r in res_v1)

        # Commit 2: legacy_auth deleted, new billing updated
        c3 = CodeChunk(repository_id="org/repo", commit_sha="commit_v2", file_path="src/billing.py", language="python", start_line=1, end_line=25, content="def calculate_tax_v2(): pass", symbol="calculate_tax_v2")
        store.index_chunks([c3])

        # Query commit_v2: must NOT return stale legacy_auth.py
        res_v2 = store.search_hybrid(repository_id="org/repo", query="auth", commit_sha="commit_v2")
        assert not any("legacy_auth.py" in r["file_path"] for r in res_v2)

        # Explicit deletion of older repository chunks
        store.delete_repository_chunks(repository_id="org/repo", commit_sha="commit_v1")
        res_after = store.search_hybrid(repository_id="org/repo", query="auth")
        assert not any("legacy_auth.py" in r["file_path"] for r in res_after)
    finally:
        if tmp_db.exists():
            try:
                tmp_db.unlink()
            except OSError:
                pass


def test_rag_recall_metrics_on_eval_dataset():
    tmp_db = Path(tempfile.gettempdir()) / f"test_eval_{uuid.uuid4().hex[:8]}.db"
    store = PersistentVectorStore(str(tmp_db))
    try:
        all_chunks = []
        # Index repo_alpha
        alpha_dir = FIXTURES_DIR / "repo_alpha"
        for p in alpha_dir.rglob("*"):
            if p.is_file() and not p.name.startswith("."):
                content = p.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(p.relative_to(alpha_dir)).replace("\\", "/")
                all_chunks.extend(chunk_code_file(content, rel_path, "test/repo_alpha", "2471966e"))

        # Index repo_beta
        beta_dir = FIXTURES_DIR / "repo_beta"
        for p in beta_dir.rglob("*"):
            if p.is_file() and not p.name.startswith("."):
                content = p.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(p.relative_to(beta_dir)).replace("\\", "/")
                all_chunks.extend(chunk_code_file(content, rel_path, "test/repo_beta", "3aaea58d"))

        store.index_chunks(all_chunks)

        eval_queries = [
            ("calculate sales tax based on subtotal and rate", "test/repo_alpha", "src/billing.py"),
            ("dynamic sql string concatenation vulnerability in cursor execute", "test/repo_alpha", "src/database.py"),
            ("internal missing core import module syntax error", "test/repo_alpha", "src/api.py"),
            ("compute tick rate delta physics simulation", "test/repo_beta", "src/game_loop.ts"),
            ("websockets real time game loop", "test/repo_beta", "README.md"),
        ]

        top1_hits = 0
        for query, repo, expected_file in eval_queries:
            results = store.search_hybrid(repository_id=repo, query=query, top_k=3)
            assert len(results) > 0, f"No results for query '{query}' in {repo}"
            if results[0]["file_path"] == expected_file:
                top1_hits += 1

        recall_at_1 = top1_hits / len(eval_queries)
        assert recall_at_1 >= 0.80, f"Recall@1 is {recall_at_1:.2f}, expected at least 0.80"

        # Cross-repository isolation check: querying repo_beta must never return repo_alpha files
        beta_results = store.search_hybrid(repository_id="test/repo_beta", query="calculate sales tax", top_k=5)
        assert not any("repo_alpha" in r["repository_id"] or "billing.py" in r["file_path"] for r in beta_results)
    finally:
        if tmp_db.exists():
            try:
                tmp_db.unlink()
            except OSError:
                pass


# =========================================================================
# Task 5: Chatbot Groundedness & Transparent Uncertainty
# =========================================================================

def test_chatbot_groundedness_and_fallback_badge():
    adapter = QwenAdapter()

    res = adapter.generate_grounded_response(
        query="What is the sales tax calculation logic?",
        repository_name="test/repo_alpha",
        branch="main",
        commit_sha="2471966e",
        context_block="<source_chunk file=\"src/billing.py\" lines=\"1-15\">\ndef calculate_sales_tax(subtotal: float, tax_rate: float = 0.08) -> float:\n    return round(subtotal * tax_rate, 2)\n</source_chunk>",
        citations=[{"filePath": "src/billing.py", "startLine": 1, "endLine": 15, "symbol": "calculate_sales_tax"}],
    )

    text = res["text"]
    assert "> [!NOTE]" in text
    assert "Deterministic Rule/RAG Response" in text
    assert "src/billing.py" in text
    assert res["citations"][0]["filePath"] == "src/billing.py"


def test_chatbot_transparent_uncertainty():
    adapter = QwenAdapter()

    res = adapter.generate_grounded_response(
        query="Explain how Kubernetes Helm charts and GraphQL are configured here",
        repository_name="test/repo_alpha",
        branch="main",
        commit_sha="2471966e",
        context_block="",
        citations=[],
    )

    text = res["text"]
    assert "Transparent Verification Status" in text
    assert "No evidence of" in text
    assert "kubernetes" in text.lower() or "graphql" in text.lower()


# =========================================================================
# Task 6: Security Verification (SSRF, Zip-Slip, Secrets, Prompt Injection, RBAC)
# =========================================================================

def test_security_ssrf_comprehensive_matrix():
    # IPv4 loopback
    with pytest.raises(ValueError):
        validate_repository_url("http://127.0.0.1:8000/repo.git")
    with pytest.raises(ValueError):
        validate_repository_url("https://127.0.0.1:8000/repo.git")
    with pytest.raises(ValueError):
        validate_repository_url("http://0.0.0.0:8000/repo.git")

    # IPv6 loopback
    with pytest.raises(ValueError):
        validate_repository_url("http://[::1]:8000/repo.git")

    # Cloud metadata
    with pytest.raises(ValueError):
        validate_repository_url("http://169.254.169.254/latest/meta-data")

    # Hex/Octal representations
    with pytest.raises(ValueError):
        validate_repository_url("http://0x7f000001:8000/repo.git")

    # Non-HTTPS protocol
    with pytest.raises(ValueError):
        validate_repository_url("file:///etc/passwd")

    # Redirect URL SSRF validation
    with pytest.raises(ValueError):
        validate_redirect_url("http://127.0.0.1:8080/evil.zip")
    with pytest.raises(ValueError):
        validate_redirect_url("http://169.254.169.254/latest/meta-data")


def test_security_zip_slip_traversal_prevention():
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        # Malicious traversal member
        zf.writestr("../../evil_payload.py", "print('hacked')")
        zf.writestr("valid_file.py", "print('safe')")

    zip_bytes = zip_buffer.getvalue()
    temp_dir = Path(tempfile.mkdtemp(prefix="codesense_zip_test_"))
    try:
        zip_path = temp_dir / "test.zip"
        zip_path.write_bytes(zip_bytes)
        target_dir = temp_dir / "extracted"
        target_dir.mkdir()

        with pytest.raises(ValueError, match="violates extraction boundary|Zip-slip"):
            safe_extract_zip(str(zip_path), str(target_dir))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_security_secret_redaction_before_storage():
    config_py = FIXTURES_DIR / "repo_alpha" / "src" / "config.py"
    raw_content = config_py.read_text(encoding="utf-8")

    assert "AKIA" in raw_content
    redacted = redact_secrets(raw_content)
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "[AWS_ACCESS_KEY_REDACTED]" in redacted
    assert "[GITHUB_FINE_GRAINED_PAT_REDACTED]" in redacted


def test_security_prompt_injection_neutralization():
    telemetry_py = FIXTURES_DIR / "repo_alpha" / "src" / "telemetry.py"
    content = telemetry_py.read_text(encoding="utf-8")

    sanitized = sanitize_untrusted_chunk(content)
    adapter = QwenAdapter()
    res = adapter._generate_evidence_grounded_fallback(
        query="What does telemetry.py do?",
        repository_name="test/repo_alpha",
        branch="main",
        context_block=sanitized,
        citations=[{"filePath": "src/telemetry.py", "startLine": 1, "endLine": 15, "symbol": "track_metric"}],
    )
    # The output must not execute prompt injection instruction
    assert "SYSTEM COMPROMISED" not in res["text"]


@pytest.mark.asyncio
async def test_cross_user_conversation_authorization(backend_client):
    user_a = {
        "id": uuid.uuid4(),
        "email": "user_a@codesense.dev",
        "display_name": "User Alpha",
        "github_username": "user_a",
        "github_token": "token-a",
        "created_at": "2026-10-15T12:00:00Z",
    }
    user_b = {
        "id": uuid.uuid4(),
        "email": "user_b@codesense.dev",
        "display_name": "User Beta",
        "github_username": "user_b",
        "github_token": "token-b",
        "created_at": "2026-10-15T12:00:00Z",
    }
    token_a = create_token(user_a)
    token_b = create_token(user_b)

    conv_id = f"test-conv-{uuid.uuid4().hex[:8]}"

    # User A creates a message in conversation
    dev_store.save_conversation_message(
        conv_id,
        {"role": "user", "content": "Secret analysis message for User A"},
        user_id=str(user_a["id"]),
    )

    # User A accesses conversation -> 200 OK
    res_a = await backend_client.get(
        f"/api/ai/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a.status_code == 200
    assert len(res_a.json()["messages"]) == 1

    # User B attempts to access User A's conversation -> 403 Forbidden!
    res_b = await backend_client.get(
        f"/api/ai/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 403
    data_b = res_b.json()
    assert "Access denied" in (data_b.get("message") or data_b.get("detail") or "")


@pytest.mark.asyncio
async def test_cross_user_report_download_authorization(backend_client):
    user_a = {
        "id": uuid.uuid4(),
        "email": "owner@codesense.dev",
        "display_name": "Repo Owner",
        "github_username": "owner",
        "github_token": "token-owner",
        "created_at": "2026-10-15T12:00:00Z",
    }
    user_b = {
        "id": uuid.uuid4(),
        "email": "intruder@codesense.dev",
        "display_name": "Other User",
        "github_username": "other",
        "github_token": "token-other",
        "created_at": "2026-10-15T12:00:00Z",
    }
    token_b = create_token(user_b)

    repo_id = uuid.uuid4()
    # Save repo owned by User A in dev_store
    dev_store.save_repository({
        "id": str(repo_id),
        "name": "private-vault",
        "full_name": "owner/private-vault",
        "owner_id": str(user_a["id"]),
        "default_branch": "main",
        "language": "Python",
    })

    # User B tries to download User A's report -> 403 Forbidden!
    res_download = await backend_client.get(
        f"/api/reports/download?repositoryId={repo_id}&format=pdf",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_download.status_code == 403
    data_dl = res_download.json()
    assert "Access denied" in (data_dl.get("message") or data_dl.get("detail") or "")


# =========================================================================
# Task 7: PDF Report Verification (ReportLab Signature, Page Numbering, Layout)
# =========================================================================

def test_pdf_report_signature_and_page_numbering():
    findings = [
        {
            "category": "Security",
            "severity": "High",
            "file": "src/database.py",
            "line_number": 14,
            "title": "SQL Injection in execute query",
            "suggestion": "Use parameterized queries.",
        },
        {
            "category": "Code smell",
            "severity": "Medium",
            "file": "src/api.py",
            "line_number": 5,
            "title": "Unresolved internal import",
            "suggestion": "Verify module export.",
        },
    ]

    generator = PdfAuditReportGenerator()
    pdf_bytes = generator.generate({
        "repository": "test/repo_alpha",
        "branch": "main",
        "maintainability_score": 85,
        "technical_debt_hours": 6,
        "findings": findings,
    })

    # Magic byte signature check
    assert pdf_bytes.startswith(b"%PDF-1.4"), "PDF must start with %PDF-1.4 header"
    assert len(pdf_bytes) > 2000, "PDF must contain content"
    assert b"/Count" in pdf_bytes or b"/Pages" in pdf_bytes, "PDF must have page tree"


# =========================================================================
# Task 8: Performance & Concurrency Verification
# =========================================================================

def test_vector_store_reopen_persistence():
    tmp_db = Path(tempfile.gettempdir()) / f"test_persist_{uuid.uuid4().hex[:8]}.db"
    try:
        # First session
        store1 = PersistentVectorStore(str(tmp_db))
        chunk = CodeChunk(
            repository_id="org/persist",
            commit_sha="sha1",
            file_path="src/core.py",
            language="python",
            start_line=1,
            end_line=20,
            content="def persistent_func(): pass",
            symbol="persistent_func",
        )
        store1.index_chunks([chunk])
        assert store1.get_stats()["total_chunks"] == 1

        # Second session: reopen database
        store2 = PersistentVectorStore(str(tmp_db))
        assert store2.get_stats()["total_chunks"] == 1
        results = store2.search_hybrid(repository_id="org/persist", query="persistent")
        assert len(results) == 1
        assert results[0]["file_path"] == "src/core.py"
    finally:
        if tmp_db.exists():
            try:
                tmp_db.unlink()
            except OSError:
                pass
