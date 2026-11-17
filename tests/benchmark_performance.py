import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ai-service"))

from app.rag.chunker import chunk_repository_directory
from app.rag.vector_store import PersistentVectorStore
from app.rag.retriever import HybridRetriever
from app.rag.llm_adapter import QwenAdapter

EVAL_FIXTURES_DIR = ROOT / "tests" / "fixtures" / "eval_repos"

BENCHMARK_SCENARIOS = [
    # 1. Simple Questions
    {
        "category": "simple",
        "repo": "repo_alpha",
        "query": "What does record_ping return in telemetry?",
        "expected_file": "src/telemetry.py",
    },
    {
        "category": "simple",
        "repo": "repo_beta",
        "query": "Where is hashPassword implemented in auth?",
        "expected_file": "src/auth.ts",
    },
    {
        "category": "simple",
        "repo": "repo_gamma",
        "query": "Where is the Spring Boot main application entrypoint CommerceApplication?",
        "expected_file": "src/main/java/com/codesense/commerce/CommerceApplication.java",
    },
    {
        "category": "simple",
        "repo": "repo_delta",
        "query": "Where is the Express app and health check endpoint initialized?",
        "expected_file": "src/server.ts",
    },

    # 2. Code Explanations
    {
        "category": "code_explanation",
        "repo": "repo_alpha",
        "query": "Where is calculate_sales_tax defined and what rate does it apply?",
        "expected_file": "src/billing.py",
    },
    {
        "category": "code_explanation",
        "repo": "repo_alpha",
        "query": "Show the get_user_by_id SQL query composition in database",
        "expected_file": "src/database.py",
    },
    {
        "category": "code_explanation",
        "repo": "repo_gamma",
        "query": "Where is calculateOrderTotal implemented with discountPercent and taxRate?",
        "expected_file": "src/main/java/com/codesense/commerce/service/OrderService.java",
    },
    {
        "category": "code_explanation",
        "repo": "repo_delta",
        "query": "How is findUserByEmail querying PostgreSQL with parameterized query $1?",
        "expected_file": "src/db/queries.ts",
    },

    # 3. Multi-file Questions
    {
        "category": "multi_file",
        "repo": "repo_gamma",
        "query": "How does OrderService call OrderRepository to find orders and return Order?",
        "expected_file": "src/main/java/com/codesense/commerce/service/OrderService.java",
    },
    {
        "category": "multi_file",
        "repo": "repo_delta",
        "query": "How is the search user route defined in userRouter and used by server?",
        "expected_file": "src/routes/users.ts",
    },
    {
        "category": "multi_file",
        "repo": "repo_gamma",
        "query": "What Maven dependencies are declared in pom.xml for Spring Data and Web?",
        "expected_file": "pom.xml",
    },
    {
        "category": "multi_file",
        "repo": "repo_delta",
        "query": "What dependencies are configured in package.json for Node Express and pg?",
        "expected_file": "package.json",
    },

    # 4. Complex Repository Reviews & Audits
    {
        "category": "complex_audit",
        "repo": "repo_gamma",
        "query": "Where is insecure deserialization ObjectInputStream used in JwtAuthFilter and how can it lead to RCE?",
        "expected_file": "src/main/java/com/codesense/commerce/security/JwtAuthFilter.java",
    },
    {
        "category": "complex_audit",
        "repo": "repo_beta",
        "query": "Where is the O(N^2) pairwise connect loop for canvas particles causing performance bottlenecks?",
        "expected_file": "src/game_loop.ts",
    },
    {
        "category": "complex_audit",
        "repo": "repo_delta",
        "query": "What schema definition creates the users table in SQL migrations with primary keys?",
        "expected_file": "src/db/migrations/001_init.sql",
    },
    {
        "category": "complex_audit",
        "repo": "repo_alpha",
        "query": "What is the asynchronous microservice architecture using Celery and Redis Streams in README?",
        "expected_file": "README.md",
    },
]


def estimate_tokens(text: str) -> int:
    """Estimates token count (~4 characters per token)."""
    return max(1, int(len(text) / 3.8))


def run_benchmark():
    tmp_dir = tempfile.mkdtemp(prefix="codesense_perf_bench_")
    db_path = os.path.join(tmp_dir, "perf_vector_store.sqlite3")
    store = PersistentVectorStore(db_path)
    retriever = HybridRetriever(store=store)
    adapter = QwenAdapter()

    print("=== CodeSense AI: Stage 2 Performance Benchmarking ===")
    print(f"Indexing test fixtures from {EVAL_FIXTURES_DIR}...")
    for repo_name in ["repo_alpha", "repo_beta", "repo_gamma", "repo_delta"]:
        repo_dir = EVAL_FIXTURES_DIR / repo_name
        chunks = chunk_repository_directory(str(repo_dir), repository_id=repo_name, commit_sha="perf-v1")
        store.index_chunks(chunks)

    results = []
    category_data = {
        "simple": [],
        "code_explanation": [],
        "multi_file": [],
        "complex_audit": [],
    }

    print("\nExecuting live timed benchmarks across 16 scenarios...")
    for item in BENCHMARK_SCENARIOS:
        cat = item["category"]
        repo = item["repo"]
        query = item["query"]

        # 1. Retrieval timing
        t_ret_start = time.perf_counter()
        context_block, citations = retriever.retrieve(
            repository_id=repo,
            query=query,
            commit_sha="perf-v1",
            top_k=5,
        )
        t_ret_end = time.perf_counter()
        retrieval_ms = (t_ret_end - t_ret_start) * 1000.0

        input_tokens = estimate_tokens(context_block) + estimate_tokens(query)

        # 2. Streaming Time to First Token (TTFT) and throughput
        t_stream_start = time.perf_counter()
        stream = adapter.generate_stream(
            query=query,
            repository_name=f"test/{repo}",
            branch="main",
            commit_sha="perf-v1",
            context_block=context_block,
            citations=citations,
        )

        first_token_time = None
        streamed_chunks = []
        for chunk in stream:
            if first_token_time is None:
                first_token_time = time.perf_counter()
            streamed_chunks.append(chunk)
        t_stream_end = time.perf_counter()

        ttft_ms = ((first_token_time - t_stream_start) * 1000.0) if first_token_time else 0.0
        stream_total_ms = (t_stream_end - t_stream_start) * 1000.0
        full_text = "".join(streamed_chunks)
        output_tokens = estimate_tokens(full_text)
        tokens_per_sec = (output_tokens / (stream_total_ms / 1000.0)) if stream_total_ms > 0 else 0.0

        # 3. Synchronous total response latency
        t_sync_start = time.perf_counter()
        sync_res = adapter.generate_grounded_response(
            query=query,
            repository_name=f"test/{repo}",
            branch="main",
            commit_sha="perf-v1",
            context_block=context_block,
            citations=citations,
        )
        t_sync_end = time.perf_counter()
        sync_total_ms = (t_sync_end - t_sync_start) * 1000.0

        record = {
            "category": cat,
            "repo": repo,
            "query": query,
            "retrieval_ms": round(retrieval_ms, 2),
            "ttft_ms": round(ttft_ms, 2),
            "stream_total_ms": round(stream_total_ms, 2),
            "sync_total_ms": round(sync_total_ms, 2),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "tokens_per_sec": round(tokens_per_sec, 2),
        }
        results.append(record)
        category_data[cat].append(record)

    all_ttfts = [r["ttft_ms"] for r in results]
    all_sync = [r["sync_total_ms"] for r in results]
    all_ret = [r["retrieval_ms"] for r in results]
    all_in_tokens = [r["input_tokens"] for r in results]
    all_out_tokens = [r["output_tokens"] for r in results]
    all_tps = [r["tokens_per_sec"] for r in results]

    def percentile(arr, p):
        s = sorted(arr)
        idx = int(math.ceil((p / 100.0) * len(s))) - 1
        return s[max(0, idx)]

    print("\n" + "=" * 70)
    print("STAGE 2 PERFORMANCE BENCHMARK RESULTS")
    print("=" * 70)
    print(f"Total Scenarios Evaluated: {len(results)}")
    print(f"Hybrid Retrieval Latency:  avg={sum(all_ret)/len(all_ret):.2f} ms | p95={percentile(all_ret, 95):.2f} ms")
    print(f"Time to First Token (TTFT): avg={sum(all_ttfts)/len(all_ttfts):.2f} ms | p95={percentile(all_ttfts, 95):.2f} ms")
    print(f"Total Response Latency:    avg={sum(all_sync)/len(all_sync):.2f} ms | p95={percentile(all_sync, 95):.2f} ms")
    print(f"Output Tokens / Second:    avg={sum(all_tps)/len(all_tps):.2f} tok/s")
    print(f"Input Tokens / Request:    avg={int(sum(all_in_tokens)/len(all_in_tokens))} tokens | max={max(all_in_tokens)}")
    print(f"Output Tokens / Request:   avg={int(sum(all_out_tokens)/len(all_out_tokens))} tokens | max={max(all_out_tokens)}")

    print("\nBreakdown by Question Category:")
    for cat, items in category_data.items():
        c_ret = sum(i["retrieval_ms"] for i in items) / len(items)
        c_ttft = sum(i["ttft_ms"] for i in items) / len(items)
        c_tot = sum(i["sync_total_ms"] for i in items) / len(items)
        c_tps = sum(i["tokens_per_sec"] for i in items) / len(items)
        c_in = int(sum(i["input_tokens"] for i in items) / len(items))
        c_out = int(sum(i["output_tokens"] for i in items) / len(items))
        print(f"  [{cat.upper():16s}] n={len(items):2d} | Ret={c_ret:.1f}ms | TTFT={c_ttft:.1f}ms | Tot={c_tot:.1f}ms | InTok={c_in} | OutTok={c_out} | TPS={c_tps:.0f}")

    # Output JSON summary
    out_path = ROOT / "benchmark_performance_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total_scenarios": len(results),
                "avg_retrieval_ms": round(sum(all_ret)/len(all_ret), 2),
                "p95_retrieval_ms": round(percentile(all_ret, 95), 2),
                "avg_ttft_ms": round(sum(all_ttfts)/len(all_ttfts), 2),
                "p95_ttft_ms": round(percentile(all_ttfts, 95), 2),
                "avg_total_latency_ms": round(sum(all_sync)/len(all_sync), 2),
                "p95_total_latency_ms": round(percentile(all_sync, 95), 2),
                "avg_tokens_per_sec": round(sum(all_tps)/len(all_tps), 2),
                "avg_input_tokens": int(sum(all_in_tokens)/len(all_in_tokens)),
                "avg_output_tokens": int(sum(all_out_tokens)/len(all_out_tokens)),
            },
            "category_metrics": {
                cat: {
                    "count": len(items),
                    "avg_retrieval_ms": round(sum(i["retrieval_ms"] for i in items) / len(items), 2),
                    "avg_ttft_ms": round(sum(i["ttft_ms"] for i in items) / len(items), 2),
                    "avg_total_ms": round(sum(i["sync_total_ms"] for i in items) / len(items), 2),
                    "avg_in_tokens": int(sum(i["input_tokens"] for i in items) / len(items)),
                    "avg_out_tokens": int(sum(i["output_tokens"] for i in items) / len(items)),
                } for cat, items in category_data.items()
            },
            "records": results,
        }, f, indent=2)
    print(f"\nSaved raw performance benchmark dataset to: {out_path.name}")
    print("[PASS] Stage 2 Performance Benchmarking completed successfully!")


if __name__ == "__main__":
    run_benchmark()
