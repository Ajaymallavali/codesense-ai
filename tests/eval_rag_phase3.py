import os
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ai-service"))
sys.path.insert(0, str(ROOT / "backend"))
import app
ai_app_path = str(ROOT / "ai-service" / "app")
if ai_app_path not in app.__path__:
    app.__path__.append(ai_app_path)

from app.rag.chunker import detect_file_language, chunk_python_code, chunk_by_sliding_window
from app.rag.vector_store import PersistentVectorStore
from app.rag.retriever import HybridRetriever, sanitize_untrusted_chunk
from app.rag.llm_adapter import QwenAdapter


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "eval_repos"


def run_comprehensive_evaluation() -> dict[str, Any]:
    tmp_db = Path(tempfile.gettempdir()) / f"eval_p3_{uuid.uuid4().hex[:8]}.db"
    store = PersistentVectorStore(str(tmp_db))
    adapter = QwenAdapter()

    try:
        # 1. Ingest Commit 1 for repo_alpha (includes legacy_auth.py from git history)
        alpha_dir = FIXTURES_DIR / "repo_alpha"
        alpha_v1_chunks = []
        for p in alpha_dir.rglob("*"):
            if p.is_file() and not p.name.startswith(".") and ".git" not in p.parts:
                content = p.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(p.relative_to(alpha_dir)).replace("\\", "/")
                lang = detect_file_language(rel_path)
                if lang == "python":
                    file_chunks = chunk_python_code(content, rel_path, "test/repo_alpha", "4c63521e")
                else:
                    lines = content.splitlines(keepends=True)
                    file_chunks = chunk_by_sliding_window(lines, rel_path, lang, "test/repo_alpha", "4c63521e")
                alpha_v1_chunks.extend(file_chunks)

        # Include historical legacy_auth.py for commit 1
        legacy_auth_content = '"""Legacy authentication to be deleted in commit 2."""\ndef legacy_authenticate(user, pw):\n    return user == "admin"\n'
        alpha_v1_chunks.extend(chunk_python_code(legacy_auth_content, "src/legacy_auth.py", "test/repo_alpha", "4c63521e"))

        # Ingest Commit 2 for repo_alpha (legacy_auth.py removed)
        alpha_v2_chunks = []
        for p in alpha_dir.rglob("*"):
            if p.is_file() and not p.name.startswith(".") and ".git" not in p.parts and "legacy_auth" not in p.name:
                content = p.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(p.relative_to(alpha_dir)).replace("\\", "/")
                lang = detect_file_language(rel_path)
                if lang == "python":
                    file_chunks = chunk_python_code(content, rel_path, "test/repo_alpha", "2471966e")
                else:
                    lines = content.splitlines(keepends=True)
                    file_chunks = chunk_by_sliding_window(lines, rel_path, lang, "test/repo_alpha", "2471966e")
                alpha_v2_chunks.extend(file_chunks)

        # Ingest repo_beta
        beta_dir = FIXTURES_DIR / "repo_beta"
        beta_chunks = []
        for p in beta_dir.rglob("*"):
            if p.is_file() and not p.name.startswith(".") and ".git" not in p.parts:
                content = p.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(p.relative_to(beta_dir)).replace("\\", "/")
                lang = detect_file_language(rel_path)
                if lang == "python":
                    file_chunks = chunk_python_code(content, rel_path, "test/repo_beta", "3aaea58d")
                else:
                    lines = content.splitlines(keepends=True)
                    file_chunks = chunk_by_sliding_window(lines, rel_path, lang, "test/repo_beta", "3aaea58d")
                beta_chunks.extend(file_chunks)

        # Store all chunks
        store.index_chunks(alpha_v1_chunks + alpha_v2_chunks + beta_chunks)

        # 12 Ground-Truth Test Cases
        cases = [
            {
                "id": "Q1",
                "query": "calculate sales tax based on subtotal and rate",
                "repo": "test/repo_alpha",
                "commit": "2471966e",
                "expected_file": "src/billing.py",
                "expected_symbol": "calculate_sales_tax",
            },
            {
                "id": "Q2",
                "query": "dynamic sql string concatenation vulnerability in cursor execute",
                "repo": "test/repo_alpha",
                "commit": "2471966e",
                "expected_file": "src/database.py",
                "expected_symbol": "execute_query",
            },
            {
                "id": "Q3",
                "query": "internal missing core import module syntax error",
                "repo": "test/repo_alpha",
                "commit": "2471966e",
                "expected_file": "src/api.py",
                "expected_symbol": "telemetry_engine",
            },
            {
                "id": "Q4",
                "query": "FastAPI backend and Redis worker architecture documentation",
                "repo": "test/repo_alpha",
                "commit": "2471966e",
                "expected_file": "README.md",
                "expected_symbol": "general",
            },
            {
                "id": "Q5",
                "query": "compute_tick_rate fps delta calculation function",
                "repo": "test/repo_beta",
                "commit": "3aaea58d",
                "expected_file": "src/game_loop.ts",
                "expected_symbol": "compute_tick_rate",
            },
            {
                "id": "Q6",
                "query": "WebSockets real time multi client game server architecture",
                "repo": "test/repo_beta",
                "commit": "3aaea58d",
                "expected_file": "README.md",
                "expected_symbol": "code_block",
            },
            {
                "id": "Q7",
                "query": "AWS credentials and GitHub access token configuration constants",
                "repo": "test/repo_alpha",
                "commit": "2471966e",
                "expected_file": "src/config.py",
                "expected_symbol": "module_header",
            },
            {
                "id": "Q8",
                "query": "track application metrics and latency telemetry",
                "repo": "test/repo_alpha",
                "commit": "2471966e",
                "expected_file": "src/telemetry.py",
                "expected_symbol": "track_metric",
            },
            {
                "id": "Q9",
                "query": "broken syntax error function definition test",
                "repo": "test/repo_alpha",
                "commit": "2471966e",
                "expected_file": "src/syntax_error_file.py",
                "expected_symbol": "code_block",
            },
            {
                "id": "Q10",
                "query": "legacy_authenticate user password check handler",
                "repo": "test/repo_alpha",
                "commit": "4c63521e", # Commit 1 where it existed
                "expected_file": "src/legacy_auth.py",
                "expected_symbol": "legacy_authenticate",
            },
        ]

        top1_hits = 0
        top3_hits = 0
        top5_hits = 0
        reciprocal_ranks = []
        latencies = []

        results_log = []

        for case in cases:
            t0 = time.time()
            res = store.search_hybrid(
                repository_id=case["repo"],
                query=case["query"],
                commit_sha=case["commit"],
                top_k=5,
            )
            lat = (time.time() - t0) * 1000
            latencies.append(lat)

            files = [r["file_path"] for r in res]
            expected = case["expected_file"]

            # Compute rank
            rank = None
            if expected in files:
                rank = files.index(expected) + 1

            if rank == 1:
                top1_hits += 1
                reciprocal_ranks.append(1.0)
            elif rank is not None:
                reciprocal_ranks.append(1.0 / rank)
            else:
                reciprocal_ranks.append(0.0)

            if rank is not None and rank <= 3:
                top3_hits += 1
            if rank is not None and rank <= 5:
                top5_hits += 1

            results_log.append({
                "id": case["id"],
                "query": case["query"],
                "target_repo": case["repo"],
                "commit": case["commit"],
                "expected_file": expected,
                "retrieved_top1": files[0] if files else "NONE",
                "rank": rank,
                "score_top1": res[0]["score"] if res else 0.0,
                "latency_ms": round(lat, 2),
            })

        # Special Test 11: Stale file deletion check
        # Legacy auth was deleted in commit 2 (2471966e). Searching commit 2 must NOT return it.
        res_deleted = store.search_hybrid(
            repository_id="test/repo_alpha",
            query="legacy authentication check",
            commit_sha="2471966e",
            top_k=5,
        )
        stale_leak = any(r["file_path"] == "src/legacy_auth.py" for r in res_deleted)

        # Special Test 12: Cross-Repository Isolation
        res_cross = store.search_hybrid(
            repository_id="test/repo_alpha",
            query="compute tick rate delta physics simulation",
            top_k=5,
        )
        cross_leak = any("repo_beta" in r["repository_id"] or "game_loop.ts" in r["file_path"] for r in res_cross)

        # Special Test 13: Abstention check on unsupported technologies
        grounded_abstention = adapter.generate_grounded_response(
            query="How is Kubernetes and GraphQL deployed?",
            repository_name="test/repo_alpha",
            branch="main",
            commit_sha="2471966e",
            context_block="",
            citations=[],
        )
        has_abstention = "Transparent Verification Status" in grounded_abstention["text"]

        total = len(cases)
        recall_at_1 = top1_hits / total
        recall_at_3 = top3_hits / total
        recall_at_5 = top5_hits / total
        mrr = sum(reciprocal_ranks) / total
        avg_latency = sum(latencies) / len(latencies)

        return {
            "total_queries": total,
            "recall_at_1": recall_at_1,
            "recall_at_3": recall_at_3,
            "recall_at_5": recall_at_5,
            "mrr": mrr,
            "avg_latency_ms": avg_latency,
            "stale_leak": stale_leak,
            "cross_leak": cross_leak,
            "has_abstention": has_abstention,
            "results_log": results_log,
        }
    finally:
        if tmp_db.exists():
            try:
                tmp_db.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    metrics = run_comprehensive_evaluation()
    print("=== PHASE 3 RAG & CHATBOT EVALUATION METRICS ===")
    print(f"Total Queries Evaluated: {metrics['total_queries']}")
    print(f"Recall@1: {metrics['recall_at_1'] * 100:.1f}%")
    print(f"Recall@3: {metrics['recall_at_3'] * 100:.1f}%")
    print(f"Recall@5: {metrics['recall_at_5'] * 100:.1f}%")
    print(f"Mean Reciprocal Rank (MRR): {metrics['mrr']:.4f}")
    print(f"Average Hybrid Search Latency: {metrics['avg_latency_ms']:.2f}ms")
    print(f"Stale Chunk Leak (Deleted Files in Commit 2): {metrics['stale_leak']}")
    print(f"Cross-Repository Data Leakage: {metrics['cross_leak']}")
    print(f"Transparent Abstention on Non-Existent Technologies: {metrics['has_abstention']}")
