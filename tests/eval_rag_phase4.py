import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Add paths
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ai-service"))

from app.rag.chunker import chunk_repository_directory
from app.rag.vector_store import PersistentVectorStore
from app.rag.retriever import HybridRetriever, sanitize_untrusted_chunk
from app.rag.llm_adapter import QwenAdapter

EVAL_FIXTURES_DIR = ROOT / "tests" / "fixtures" / "eval_repos"

EVAL_QUERIES = [
    # --- REPO ALPHA (Python / Flask / SQL) ---
    {
        "repo": "repo_alpha",
        "query": "Where is calculate_sales_tax defined and what rate does it apply?",
        "expected_file": "src/billing.py",
        "expected_symbol": "calculate_sales_tax",
        "category": "code_explanation",
    },
    {
        "repo": "repo_alpha",
        "query": "How is apply_promotional_discount implemented for discount codes?",
        "expected_file": "src/billing.py",
        "expected_symbol": "apply_promotional_discount",
        "category": "simple",
    },
    {
        "repo": "repo_alpha",
        "query": "Show the get_user_by_id SQL query composition in database",
        "expected_file": "src/database.py",
        "expected_symbol": "get_user_by_id",
        "category": "code_explanation",
    },
    {
        "repo": "repo_alpha",
        "query": "Where is handle_request API router defined importing secret_token_generator?",
        "expected_file": "src/api.py",
        "expected_symbol": "handle_request",
        "category": "code_explanation",
    },
    {
        "repo": "repo_alpha",
        "query": "Where are AWS_ACCESS_KEY and DEBUG_MODE configured in config settings?",
        "expected_file": "src/config.py",
        "expected_symbol": "AWS_ACCESS_KEY",
        "category": "simple",
    },
    {
        "repo": "repo_alpha",
        "query": "What does record_ping return in telemetry ping service?",
        "expected_file": "src/telemetry.py",
        "expected_symbol": "record_ping",
        "category": "simple",
    },
    {
        "repo": "repo_alpha",
        "query": "Show the broken_function deliberate syntax error definition",
        "expected_file": "src/syntax_error_file.py",
        "expected_symbol": "broken_function",
        "category": "code_explanation",
    },
    {
        "repo": "repo_alpha",
        "query": "What is the asynchronous microservice architecture using Celery and Redis Streams?",
        "expected_file": "README.md",
        "expected_symbol": "code_block",
        "category": "code_explanation",
    },

    # --- REPO BETA (TypeScript / React / Canvas) ---
    {
        "repo": "repo_beta",
        "query": "Where is hashPassword implemented in auth?",
        "expected_file": "src/auth.ts",
        "expected_symbol": "hashPassword",
        "category": "simple",
    },
    {
        "repo": "repo_beta",
        "query": "Show verifyPassword implementation",
        "expected_file": "src/auth.ts",
        "expected_symbol": "verifyPassword",
        "category": "simple",
    },
    {
        "repo": "repo_beta",
        "query": "How is createSessionToken generating JWT tokens?",
        "expected_file": "src/auth.ts",
        "expected_symbol": "createSessionToken",
        "category": "code_explanation",
    },
    {
        "repo": "repo_beta",
        "query": "How does parseSession validate authenticated cookies?",
        "expected_file": "src/auth.ts",
        "expected_symbol": "parseSession",
        "category": "code_explanation",
    },
    {
        "repo": "repo_beta",
        "query": "Where is the main renderGameLoop animation cycle defined?",
        "expected_file": "src/game_loop.ts",
        "expected_symbol": "renderGameLoop",
        "category": "multi_file",
    },
    {
        "repo": "repo_beta",
        "query": "How does updateEntities update particle physics coordinates?",
        "expected_file": "src/game_loop.ts",
        "expected_symbol": "updateEntities",
        "category": "code_explanation",
    },
    {
        "repo": "repo_beta",
        "query": "Where is the O(N^2) pairwise connect loop for canvas particles?",
        "expected_file": "src/game_loop.ts",
        "expected_symbol": "connectParticles",
        "category": "complex_audit",
    },
    {
        "repo": "repo_beta",
        "query": "How are entity collisions checked in checkCollisions?",
        "expected_file": "src/game_loop.ts",
        "expected_symbol": "checkCollisions",
        "category": "code_explanation",
    },

    # --- REPO GAMMA (Java / Spring Boot / JPA) ---
    {
        "repo": "repo_gamma",
        "query": "Where is the Spring Boot main application entrypoint CommerceApplication?",
        "expected_file": "src/main/java/com/codesense/commerce/CommerceApplication.java",
        "expected_symbol": "CommerceApplication",
        "category": "simple",
    },
    {
        "repo": "repo_gamma",
        "query": "What endpoint does OrderController expose for fetching orders?",
        "expected_file": "src/main/java/com/codesense/commerce/controller/OrderController.java",
        "expected_symbol": "getOrderById",
        "category": "code_explanation",
    },
    {
        "repo": "repo_gamma",
        "query": "How is processCheckout mapped in OrderController?",
        "expected_file": "src/main/java/com/codesense/commerce/controller/OrderController.java",
        "expected_symbol": "processCheckout",
        "category": "code_explanation",
    },
    {
        "repo": "repo_gamma",
        "query": "Where is calculateOrderTotal implemented with discountPercent and taxRate?",
        "expected_file": "src/main/java/com/codesense/commerce/service/OrderService.java",
        "expected_symbol": "calculateOrderTotal",
        "category": "code_explanation",
    },
    {
        "repo": "repo_gamma",
        "query": "How does OrderService call OrderRepository to find orders?",
        "expected_file": "src/main/java/com/codesense/commerce/service/OrderService.java",
        "expected_symbol": "findOrderById",
        "category": "multi_file",
    },
    {
        "repo": "repo_gamma",
        "query": "Where is validateJwtToken defined in Spring Security JwtAuthFilter?",
        "expected_file": "src/main/java/com/codesense/commerce/security/JwtAuthFilter.java",
        "expected_symbol": "validateJwtToken",
        "category": "code_explanation",
    },
    {
        "repo": "repo_gamma",
        "query": "Where is insecure deserialization ObjectInputStream used in JwtAuthFilter?",
        "expected_file": "src/main/java/com/codesense/commerce/security/JwtAuthFilter.java",
        "expected_symbol": "deserializeSession",
        "category": "complex_audit",
    },
    {
        "repo": "repo_gamma",
        "query": "What Maven dependencies are declared in pom.xml?",
        "expected_file": "pom.xml",
        "expected_symbol": "dependencies",
        "category": "multi_file",
    },

    # --- REPO DELTA (Node.js / Express / SQL) ---
    {
        "repo": "repo_delta",
        "query": "Where is the Express app and health check endpoint initialized?",
        "expected_file": "src/server.ts",
        "expected_symbol": "health",
        "category": "simple",
    },
    {
        "repo": "repo_delta",
        "query": "How is findUserByEmail querying PostgreSQL with parameterized query $1?",
        "expected_file": "src/db/queries.ts",
        "expected_symbol": "findUserByEmail",
        "category": "code_explanation",
    },
    {
        "repo": "repo_delta",
        "query": "Show the listActiveAccounts SQL query with JOIN and status filter",
        "expected_file": "src/db/queries.ts",
        "expected_symbol": "listActiveAccounts",
        "category": "code_explanation",
    },
    {
        "repo": "repo_delta",
        "query": "Where is computeInvoiceSummary implemented in billingService?",
        "expected_file": "src/services/billingService.ts",
        "expected_symbol": "computeInvoiceSummary",
        "category": "code_explanation",
    },
    {
        "repo": "repo_delta",
        "query": "How is the search user route defined in userRouter?",
        "expected_file": "src/routes/users.ts",
        "expected_symbol": "userRouter",
        "category": "multi_file",
    },
    {
        "repo": "repo_delta",
        "query": "What schema definition creates the users table in SQL migrations?",
        "expected_file": "src/db/migrations/001_init.sql",
        "expected_symbol": "users",
        "category": "complex_audit",
    },
    {
        "repo": "repo_delta",
        "query": "Show the accounts balance table schema and foreign key in 001_init.sql",
        "expected_file": "src/db/migrations/001_init.sql",
        "expected_symbol": "accounts",
        "category": "code_explanation",
    },
    {
        "repo": "repo_delta",
        "query": "What dependencies are configured in package.json for Node Express?",
        "expected_file": "package.json",
        "expected_symbol": "dependencies",
        "category": "simple",
    },
]


def run_phase4_evaluation():
    tmp_dir = tempfile.mkdtemp(prefix="codesense_phase4_rag_")
    db_path = os.path.join(tmp_dir, "phase4_vector_store.sqlite3")
    store = PersistentVectorStore(db_path)
    retriever = HybridRetriever(store=store)
    adapter = QwenAdapter()

    print(f"Indexing 4 multi-language repositories into {db_path}...")
    repo_counts = {}

    for repo_name in ["repo_alpha", "repo_beta", "repo_gamma", "repo_delta"]:
        repo_dir = EVAL_FIXTURES_DIR / repo_name
        assert repo_dir.exists(), f"Missing fixture directory: {repo_dir}"
        chunks = chunk_repository_directory(str(repo_dir), repository_id=repo_name, commit_sha="commit-v1")
        store.index_chunks(chunks)
        repo_counts[repo_name] = len(chunks)
        print(f"  • {repo_name}: {len(chunks)} AST/lexical chunks indexed")

    print("\nExecuting Phase 4 RAG Accuracy Benchmark (32 queries across 4 languages)...")

    recall_at_1 = 0
    recall_at_3 = 0
    recall_at_5 = 0
    rr_total = 0.0
    latencies = []
    category_metrics = {"simple": [], "code_explanation": [], "multi_file": [], "complex_audit": []}

    valid_citations_count = 0
    total_citations_checked = 0
    unsupported_claims_count = 0

    for idx, item in enumerate(EVAL_QUERIES, start=1):
        repo = item["repo"]
        query = item["query"]
        expected_file = item["expected_file"]
        cat = item["category"]

        t0 = time.time()
        context_block, citations = retriever.retrieve(
            repository_id=repo,
            query=query,
            commit_sha="commit-v1",
            top_k=5,
        )
        t_el = (time.time() - t0) * 1000.0
        latencies.append(t_el)
        category_metrics[cat].append(t_el)

        retrieved_files = [c["filePath"] for c in citations]

        # Verify cross-repo isolation: no chunk from other repo should appear
        for c in citations:
            total_citations_checked += 1
            # Check file exists in target repo fixture
            expected_disk_file = EVAL_FIXTURES_DIR / repo / c["filePath"]
            if expected_disk_file.exists():
                valid_citations_count += 1

        # Check rankings
        rank = -1
        for i, f in enumerate(retrieved_files):
            if f.replace("\\", "/") == expected_file.replace("\\", "/"):
                rank = i + 1
                break

        if rank != 1:
            print(f"[MISS RANK 1] Query #{idx} ({repo}): '{query}' -> Expected: {expected_file}, Rank: {rank}, Got: {retrieved_files[:3]}")

        if rank == 1:
            recall_at_1 += 1
            recall_at_3 += 1
            recall_at_5 += 1
            rr_total += 1.0
        elif 1 < rank <= 3:
            recall_at_3 += 1
            recall_at_5 += 1
            rr_total += 1.0 / rank
        elif 3 < rank <= 5:
            recall_at_5 += 1
            rr_total += 1.0 / rank

        # Test synthesis through Qwen adapter (fallback or live)
        res = adapter.generate_grounded_response(
            query=query,
            repository_name=f"test/{repo}",
            branch="main",
            commit_sha="commit-v1",
            context_block=context_block,
            citations=citations,
        )
        ans_text = res.get("text", "")
        # Check that answer is grounded and doesn't invent non-existent tech
        if "graphql" in ans_text.lower() and "no evidence of graphql" not in ans_text.lower():
            unsupported_claims_count += 1

    total_q = len(EVAL_QUERIES)
    r1_pct = (recall_at_1 / total_q) * 100.0
    r3_pct = (recall_at_3 / total_q) * 100.0
    r5_pct = (recall_at_5 / total_q) * 100.0
    mrr = rr_total / total_q
    avg_lat = sum(latencies) / len(latencies)
    latencies_sorted = sorted(latencies)
    p95_lat = latencies_sorted[int(len(latencies_sorted) * 0.95)]
    citation_validity = (valid_citations_count / max(1, total_citations_checked)) * 100.0

    print("\n" + "=" * 60)
    print("PHASE 4 RAG ACCURACY & GROUNDEDNESS BENCHMARK")
    print("=" * 60)
    print(f"Total Evaluated Questions: {total_q}")
    print(f"Programming Languages Covered: Python, TypeScript, React, Java, Spring Boot, Node.js, SQL")
    print(f"Recall@1: {r1_pct:.1f}%")
    print(f"Recall@3: {r3_pct:.1f}%")
    print(f"Recall@5: {r5_pct:.1f}%")
    print(f"Mean Reciprocal Rank (MRR): {mrr:.4f}")
    print(f"Citation Validity Rate: {citation_validity:.1f}% ({valid_citations_count}/{total_citations_checked})")
    print(f"Unsupported Claim Rate: {unsupported_claims_count} ({unsupported_claims_count / total_q * 100.0:.1f}%)")
    print(f"Average Hybrid Retrieval Latency: {avg_lat:.2f} ms")
    print(f"p95 Hybrid Retrieval Latency: {p95_lat:.2f} ms")

    print("\nLatency Breakdown by Question Category:")
    for cat, times in category_metrics.items():
        cat_avg = sum(times) / len(times) if times else 0
        print(f"  • {cat:20s}: avg={cat_avg:.2f}ms (n={len(times)})")

    # Assertions
    assert r1_pct >= 90.0, f"Recall@1 {r1_pct}% below 90% threshold"
    assert r3_pct >= 95.0, f"Recall@3 {r3_pct}% below 95% threshold"
    assert mrr >= 0.90, f"MRR {mrr:.4f} below 0.90 threshold"
    assert citation_validity == 100.0, f"Citation validity {citation_validity}% not 100%"
    assert unsupported_claims_count == 0, f"Detected {unsupported_claims_count} unsupported claims"

    print("\n[PASS] Phase 4 RAG Accuracy & Grounding PASSED ALL BENCHMARKS!")
    return {
        "total_queries": total_q,
        "recall_at_1": r1_pct,
        "recall_at_3": r3_pct,
        "recall_at_5": r5_pct,
        "mrr": round(mrr, 4),
        "citation_validity": citation_validity,
        "avg_latency_ms": round(avg_lat, 2),
        "p95_latency_ms": round(p95_lat, 2),
        "category_metrics": {k: round(sum(v)/len(v), 2) for k, v in category_metrics.items()},
    }


if __name__ == "__main__":
    run_phase4_evaluation()
