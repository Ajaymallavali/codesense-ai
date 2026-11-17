# CodeSense AI — Phase 3 Implementation Plan: Production Integration, Persistence & Real-World Validation

**Date**: 2026-10-28  
**Author**: Senior Software Architect, Security Engineer & QA Lead  
**Target System**: CodeSense AI Platform (React/Vite + FastAPI Backend + FastAPI AI Service + PostgreSQL + Redis + SQLite Vector Store + Gemini LLM)

---

## 1. Executive Overview & Architectural Baseline

CodeSense AI provides automated repository auditing, multi-language static AST scanning, hybrid RAG repository intelligence, and server-side PDF audit reports. 

Phase 2 verified:
- 50 passing backend and AI service Pytest tests.
- 12 passing frontend Vitest tests.
- Successful Vite production bundle (2,470 modules, 0 TypeScript errors).
- Calibrated AST chunking, token-specificity weighted BM25, and hybrid vector retrieval achieving Recall@1 = 100% on baseline evaluation queries.
- SSRF prevention (IPv4, IPv6, cloud metadata, redirects), Zip-slip archive extraction protection, secret redaction, and cross-user authorization.

Phase 3 focuses on production readiness:
1. **Live Gemini Integration**: Unified LLM adapter with retries, rate-limit backoff, timeouts, citation enforcement, and honest handling of unconfigured API keys.
2. **PostgreSQL Persistence**: Complete database schema and Alembic migrations for users, repositories, analyses, findings, organizations, conversations, messages, and report metadata.
3. **Redis Task Coordination & Caching**: Eliminating double-execution hazards between FastAPI background tasks and dedicated Redis workers, implementing atomic state transitions and safe result caching.
4. **Repository Analysis Reliability & Incremental Indexing**: SHA-based commit tracking, change delta detection, and stale chunk pruning.
5. **RAG & Chat Quality Benchmarking**: Comprehensive multi-query, multi-repository evaluation recorded in `PHASE3_RAG_EVALUATION.md`.
6. **PDF Reports & UI Enhancements**: Validated data binding from persisted analysis records and enhanced frontend conversation handling.
7. **Docker & Deployment Hardening**: Audited Compose configuration, service networking, health checks, and non-root container specifications.
8. **Final Regression & Verification**: Documented in `PHASE3_VERIFICATION_REPORT.md`.

---

## 2. Component Audit & Gap Analysis

| Component | Current State | Reusable Assets | Gaps & Required Changes |
| :--- | :--- | :--- | :--- |
| **Gemini Integration** | Dual implementation (`call_gemini` in `main.py` vs `GeminiAdapter` in `llm_adapter.py`). Unconfigured in `.env`. | `GeminiAdapter` retry logic, prompt framing, deterministic fallback engine. | Unify `call_gemini` into `GeminiAdapter`. Enforce model selection via `GEMINI_MODEL`. Add unit tests mocking HTTP 200, 400, 401, 429, 503, timeout, and malformed JSON. Report unconfigured credentials honestly. |
| **Database & Persistence** | PostgreSQL models in `database.py` and Alembic `001_initial_schema.py`. Falls back to in-memory `DevStore` when DB is offline. | psycopg pool connection manager in `database.py`, existing CRUD queries. | Alembic schema lacks `conversations`, `conversation_messages`, and `reports`. Add migration `002_conversations_and_reports.py`. Support seamless database persistence with DevStore as dev/test fallback. |
| **Redis & Workers** | `jobs.py` dispatches to Redis AND schedules FastAPI `BackgroundTasks`. `worker.py` listens on `codesense:queue:analysis`. | Worker polling loop, Redis health check, status hash caching. | Race hazard: duplicate job execution when both worker and background tasks run. Implement atomic DB claim (`UPDATE ... WHERE status = 'PENDING' RETURNING id`) and dispatch to Redis *or* background task if Redis is offline. |
| **Repository Ingestion** | Ingests via GitHub zipball and shallow git cache in `IncrementalRepoManager`. | Tar/zip safe extraction, AST scanners, AST chunking. | Explicitly track commit SHA per file chunk. Add stale chunk invalidation on commit changes. |
| **RAG & Chat Quality** | 5 baseline evaluation queries verified in Phase 2. | Persistent vector store, hybrid retriever, token-specificity BM25. | Expand to multi-repository, multi-language benchmark suite evaluating symbols, imports, multi-file queries, commit diffs, deleted files, and prompt injections. Record in `PHASE3_RAG_EVALUATION.md`. |
| **PDF Reporting** | ReportLab `PdfAuditReportGenerator` with `NumberedCanvas` page numbering. | Custom styles, table rendering, magic bytes `%PDF-1.4`. | Bind strictly to persisted database analysis records. Handle empty findings cleanly. |
| **Frontend Integration** | React 18 / Vite / TypeScript with chat citations and report cards. | `aiApi.ts`, `analysisApi.ts`, `reportApi.ts`, `Analysis.tsx`, `Reports.tsx`. | Add `getConversation` to `aiApi.ts`. Ensure error handling and deterministic fallback badges render cleanly. |
| **Docker Compose** | Services for `postgres`, `redis`, `ai-service`, `backend`, `frontend`. | Existing service definitions and container names. | Verify volume persistence, service dependency health checks, non-root user execution, and environment variable propagation. |

---

## 3. Detailed Stage-by-Stage Implementation Plan

### Stage 2 — Live Gemini Integration & Mocked Verification Suite
- **Files to Modify**:
  - `ai-service/app/rag/llm_adapter.py`: Ensure `GeminiAdapter` supports environment-configured models (e.g. `GEMINI_MODEL`, defaulting to `gemini-1.5-flash`), sanitized logging (never logging API keys), and structured prompt output formatting.
  - `ai-service/app/main.py`: Refactor `call_gemini` and `/explain` to use `GeminiAdapter`.
  - `tests/test_gemini_integration.py`: Create dedicated test suite testing:
    - Successful Gemini generation with citations (mocked HTTP 200).
    - Missing `GEMINI_API_KEY` (transparent deterministic fallback).
    - Invalid API key (HTTP 400/401 handling).
    - Rate limit (HTTP 429) exponential backoff and retry.
    - Transient server error (HTTP 503) retry.
    - Timeout and malformed response resilience.
    - Transparent uncertainty on non-existent technology questions.
- **Verification**: Run `python -m pytest tests/test_gemini_integration.py -v`.

### Stage 3 — PostgreSQL Persistence & Alembic Migration
- **Files to Modify**:
  - `backend/migrations/versions/002_conversations_and_reports.py`: Create migration for:
    - `conversations`: `id` (VARCHAR/UUID PK), `repository_id` (UUID FK), `user_id` (UUID FK), `title` (VARCHAR), `created_at` (TIMESTAMP).
    - `conversation_messages`: `id` (UUID PK), `conversation_id` (VARCHAR/UUID FK), `role` (VARCHAR), `content` (TEXT), `citations` (JSONB/TEXT), `created_at` (TIMESTAMP).
    - `reports`: `id` (UUID PK), `repository_id` (UUID FK), `owner_id` (UUID FK), `report_type` (VARCHAR), `format` (VARCHAR), `analysis_id` (UUID FK), `created_at` (TIMESTAMP).
  - `backend/app/database.py`: Include `conversations`, `conversation_messages`, and `reports` in `initialize_database()` DDL statements.
  - `backend/app/api/ai.py` & `backend/app/api/reports.py`: Add database query paths with rollback safety and ownership verification before dev_store fallback.
  - `tests/test_database_persistence.py`: Test migration execution, CRUD operations for conversations/messages/reports, and data survival across simulated service restarts.
- **Verification**: Run `python -m pytest tests/test_database_persistence.py -v`.

### Stage 4 — Redis Task Coordination & Idempotent Processing
- **Files to Modify**:
  - `backend/app/jobs.py`:
    - Fix `dispatch_analysis_job`: If Redis client is online, enqueue to `codesense:queue:analysis` and skip adding to `BackgroundTasks` (preventing double execution). If Redis is offline, gracefully schedule via `BackgroundTasks`.
    - Fix `process_analysis_job`: Use atomic state claim `UPDATE analyses SET status = 'SCANNING', progress = 35 WHERE id = %s AND status = 'PENDING' RETURNING id`. If no row updated, exit cleanly.
    - Add safe Redis caching for latest analysis summaries (`codesense:analysis:latest:{repo_id}`) with 1-hour TTL and cache busting on new triggers.
  - `tests/test_redis_coordination.py`: Test queue push/pop, double execution prevention, atomic state locking, and Redis-offline graceful fallback.
- **Verification**: Run `python -m pytest tests/test_redis_coordination.py -v`.

### Stage 5 — Repository Analysis Reliability & Incremental Indexing
- **Files to Modify**:
  - `ai-service/app/main.py` & `ai-service/app/rag/vector_store.py`:
    - Implement commit-tagged indexing: Each chunk stores `commit_sha`.
    - In `vector_store.py`, ensure `delete_repository_chunks(repository_id, commit_sha)` purges outdated chunks when updating a repository to a new commit.
    - Add file size guard (500KB max per file) and binary file skip in repository walker.
  - `tests/test_incremental_analysis.py`: Test multi-commit updates, deletion of stale chunks, and multi-language parsing resilience.
- **Verification**: Run `python -m pytest tests/test_incremental_analysis.py -v`.

### Stage 6 — Comprehensive RAG & Chatbot Benchmark Evaluation
- **Artifact**: `PHASE3_RAG_EVALUATION.md`.
- **Benchmark Suite**:
  - Build evaluation runner evaluating 12+ queries across `repo_alpha` and `repo_beta` testing:
    1. Exact symbol lookup (`calculate_sales_tax`, `computeTickRate`).
    2. Imports and module docstrings (`internal_missing_core`, `OrderManager`).
    3. Multi-file architecture synthesis (FastAPI + Redis worker architecture from README).
    4. Security finding explanation (SQL injection in `database.py`).
    5. Commit diffs & deleted file handling (`src/legacy_auth.py` absent in commit 2).
    6. Non-existent file abstention ("Does `kubernetes.yaml` exist?").
    7. Adversarial prompt injection defense (`src/telemetry.py`).
    8. Cross-tenant repository isolation.
  - Measure: Recall@1, Recall@3, Recall@5, MRR, citation validity, and hallucination rate.

### Stage 7 — PDF Reports & Frontend Integration
- **Files to Modify**:
  - `backend/app/api/reports.py`: Ensure PDF generation accurately pulls persisted findings and metrics from the database/dev_store.
  - `frontend/src/services/aiApi.ts`: Add `getConversation(conversationId: string): Promise<{ conversationId: string; messages: ChatMessage[] }>`.
  - `frontend/src/pages/Analysis.tsx`: Support restoring conversation history when navigating back.
- **Verification**: Run `npm.cmd test --prefix frontend -- --run` and `npm.cmd run build --prefix frontend`.

### Stage 8 — Docker Compose & Deployment Readiness
- **Files to Modify**:
  - `docker-compose.yml`: Verify volume declarations, health check intervals, port mappings, and service network definitions.
  - Verify Dockerfiles in `docker/`: Check non-root execution, minimal layers, and secret absence.
  - Document local run and cloud production configuration in `PHASE3_VERIFICATION_REPORT.md`.

### Stage 9 — Final Verification & Deliverable Documentation
- **Deliverable**: `PHASE3_VERIFICATION_REPORT.md`.
- Run all test suites:
  - `python -m pytest tests/ -v`
  - `npm.cmd test --prefix frontend -- --run`
  - `npm.cmd run build --prefix frontend`
- Record all exact commands, exit codes, and verification artifacts.

---

## 4. Risk Mitigation & Dependency Matrix

| Risk | Likelihood | Impact | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **No Live Gemini API Key in Environment** | High | Low | Mock Gemini API for automated tests; preserve deterministic RAG fallback for runtime; transparently report unconfigured key status. |
| **Docker Desktop Daemon Not Running Headlessly on Windows** | High | Medium | Verify PostgreSQL and Redis connection fallbacks; execute Alembic migrations on available connection; test database persistence with simulated restart tests. |
| **Breaking Existing Phase 2 Tests** | Medium | High | Run `python -m pytest tests/ -v` after each stage; never modify test assertions without verifying regression safety. |
| **Worker Collision Race Conditions** | Low | High | Enforce atomic SQL row claims and distinct worker/background task branching. |

---

*End of Implementation Plan. Ready to execute Stage 2.*
