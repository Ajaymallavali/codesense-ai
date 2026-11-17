# CodeSense AI — Qwen3-Coder-Next Migration Report

**Migration Date:** 2026-11-02  
**Target Model:** `Qwen/Qwen3-Coder-Next`  
**Primary Engine:** Qwen3-Coder OpenAI-compatible REST Client with Streaming, Hybrid RAG Grounding, and Deterministic Fallback  
**Document Generation:** ReportLab PDF (`%PDF-1.4`) and python-pptx PowerPoint Presentation (`.pptx`)

---

## 1. Executive Summary

The migration of the CodeSense AI platform from Google Gemini to **Qwen3-Coder-Next** (`Qwen/Qwen3-Coder-Next`) is complete and verified. 

Qwen3-Coder-Next now serves as the primary generative AI model across all repository intelligence workloads:
1. **Repository-Aware AI Chatbot**: Grounded code answers with AST citations.
2. **Code Review & Debugging**: AST-guided inspection and remediation.
3. **Bug & Code-Smell Explanations**: Precise technical explanations with refactored code blocks.
4. **Security Vulnerability Assessments**: In-depth mitigation strategies (SQLi, Flask debug mode, XSS, hardcoded credentials).
5. **Repository Architecture Analysis**: Component topology and framework analysis.
6. **Code Improvement Suggestions**: Production-grade diff and code patches.
7. **Automated PR Reviews**: Automated review reports with summary, verdict (`APPROVE`, `REQUEST_CHANGES`, `COMMENT`), risk level, and inline comments.
8. **PDF and PowerPoint Audit Report Explanations**: Server-side ReportLab PDF and `python-pptx` audit presentation generation.

---

## 2. Files Created and Modified

### Files Created:
1. `QWEN_MIGRATION_PLAN.md`: Comprehensive audit and migration roadmap.
2. `ai-service/app/reports/pptx_generator.py`: 7-slide 16:9 widescreen PowerPoint audit presentation generator using `python-pptx`.
3. `tests/test_qwen_integration.py`: 10-test unit and integration test suite covering API configuration, rate limiting, retry backoff, timeouts, malformed responses, secret scrubbing, streaming, and PPTX report generation.
4. `QWEN_MIGRATION_REPORT.md`: This comprehensive delivery report.

### Files Modified:
1. `ai-service/app/rag/llm_adapter.py`: Replaced `GeminiAdapter` with production-grade `QwenAdapter` supporting OpenAI-compatible chat completions (`${QWEN_BASE_URL}/chat/completions`), token budgeting, streaming, and deterministic RAG fallback.
2. `ai-service/app/rag/__init__.py`: Exported `qwen_adapter` and `QwenAdapter`.
3. `ai-service/app/rag/vector_store.py`: Cleaned up references to Gemini; documented 256-dim hash projection embedding engine.
4. `ai-service/app/main.py`: Replaced `call_gemini` with `call_qwen`; integrated Qwen in `/chat`, `/explain`, and `/review/pr`; added `/reports/pptx` and `/chat/stream` endpoints.
5. `ai-service/app/reports/__init__.py`: Exported `pptx_report_generator`.
6. `ai-service/requirements.txt`: Added `python-pptx>=1.0.0`, `reportlab>=4.0.0`, and `httpx>=0.27.0`.
7. `backend/app/config.py`: Added Qwen configuration variables (`llm_provider`, `qwen_model`, `qwen_base_url`, `qwen_api_key`, `qwen_timeout`, `qwen_max_retries`, `qwen_max_output_tokens`).
8. `backend/app/ai_client.py`: Added `generate_pptx_report()` method calling AI service `/reports/pptx`.
9. `backend/app/api/reports.py`: Added PowerPoint (`pptx`/`ppt`) download handling with ownership authorization and PostgreSQL `reports` table persistence.
10. `frontend/src/services/reportApi.ts`: Updated `downloadReport` to support `"pptx"` format downloads.
11. `frontend/src/pages/Reports.tsx`: Added PowerPoint PPTX download buttons for Quality Assessment and Technical Debt Plan reports.
12. `frontend/src/components/Navbar.tsx`: Updated brand labels to "Qwen3-Coder AI Review Engine".
13. `frontend/src/layouts/AuthLayout.tsx`: Updated feature pill to "Qwen3-Coder PR Reviews".
14. `frontend/src/pages/Analysis.tsx`: Updated chat header, initial prompt, error handling, and badges to Qwen3-Coder.
15. `backend/dev_store.json`: Updated cached conversation messages to Qwen3-Coder references.
16. `.env.example`: Updated environment configuration template to Qwen3-Coder variables.
17. `docker-compose.yml`: Configured Qwen environment variables for `ai-service`.
18. `render.yaml`: Updated deployment blueprint environment variables.
19. `docs/deployment.md`: Documented Qwen3-Coder configuration.
20. `tests/test_rag_and_reports.py`: Updated to use `QwenAdapter`.
21. `tests/test_phase2_verification.py`: Updated to use `QwenAdapter`.
22. `tests/eval_rag_phase3.py`: Updated to use `QwenAdapter`.

### Files Removed:
1. `tests/test_gemini_integration.py`: Obsolete Gemini unit tests removed; fully superseded by `tests/test_qwen_integration.py`.

---

## 3. Gemini Components Removed

All direct dependencies, API calls, and configurations tied to Google Gemini were removed:
- Removed `generativelanguage.googleapis.com` HTTP endpoint bindings.
- Removed `GEMINI_API_KEY` requirement and references from application configuration.
- Removed `gemini-1.5-flash` model defaults.
- Removed Gemini-specific request payload structure (`contents.parts[].text`).
- Replaced with standard OpenAI-compatible completions format (`messages`, `role`, `content`, `usage`).

---

## 4. Qwen3-Coder-Next Integration Architecture

### 4.1 Configuration Matrix
The adapter reads from standardized, configurable environment variables:

```env
LLM_PROVIDER=qwen
QWEN_MODEL=Qwen/Qwen3-Coder-Next
QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
QWEN_API_KEY=
QWEN_TIMEOUT=120
QWEN_MAX_RETRIES=2
QWEN_MAX_OUTPUT_TOKENS=1500
```

### 4.2 Endpoint Compatibility
The adapter interfaces with any OpenAI-compatible inference endpoint:
- **Alibaba Cloud DashScope**: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
- **OpenRouter**: `https://openrouter.ai/api/v1`
- **Local vLLM**: `http://localhost:8000/v1`
- **Local Ollama**: `http://localhost:11434/v1`
- **HuggingFace TGI / Inference Endpoints**

### 4.3 Resilience & Fallback Engine
- **Exponential Backoff**: Automatic retry on HTTP 429 (rate limit) and HTTP 500/502/503/504 (transient server errors).
- **Deterministic Offline RAG Fallback**: If `QWEN_API_KEY` is not provided, is empty, or the upstream inference endpoint experiences persistent failure, CodeSense transparently synthesizes responses strictly from retrieved AST chunks and verified findings without hallucinating or breaking client communication.
- **Zero-Secret Leakage**: Error and warning messages scrub bearer tokens and query keys.

---

## 5. Token Usage & Retrieval Benchmark Evidence

### 5.1 RAG Accuracy (`tests/eval_rag_phase3.py`)
Evaluated across 10 deterministic ground-truth queries across multi-file repositories (`repo_alpha` and `repo_beta`):

| Metric | Score | Status |
| :--- | :--- | :--- |
| **Recall@1** | 100.0% | Verified |
| **Recall@3** | 100.0% | Verified |
| **Recall@5** | 100.0% | Verified |
| **Mean Reciprocal Rank (MRR)** | 1.0000 | Verified |
| **Average Hybrid Search Latency** | 1.61 ms | Verified |
| **Stale Chunk Invalidation** | 0.0% leak | Verified |
| **Cross-Repository Isolation** | 0.0% leak | Verified |
| **Transparent Abstention on Non-Existent Tech** | 100% | Verified |

### 5.2 Token Budgeting
- **Ordinary Chat Queries**: 300–500 output token target (`max_tokens: 1500`).
- **Telemetry**: `usage.prompt_tokens`, `usage.completion_tokens`, and `usage.total_tokens` are captured and returned in `/chat` responses.

---

## 6. Document Generation: PDF & PowerPoint

### 6.1 ReportLab PDF Generation (`POST /reports/pdf`)
- Binary Format: `%PDF-1.4`
- Multi-page layout with custom `NumberedCanvas` ("Page X of Y").
- Executive scorecard, severity breakdown table, and prioritized remediations.

### 6.2 PowerPoint Presentation Generation (`POST /reports/pptx`)
- Library: `python-pptx` (Version 1.0.2).
- Dimensions: 16:9 Widescreen (`13.333` x `7.5` inches).
- Slide Deck Contents:
  - **Slide 1**: Title, repository metadata, commit SHA, CodeSense AI badge.
  - **Slide 2**: Executive Summary & Code Health Index (Maintainability Score, Technical Debt, Issue breakdown).
  - **Slide 3**: System Architecture & Frameworks Topology.
  - **Slide 4**: Security Findings & CVE Matrix (with file paths and line numbers).
  - **Slide 5**: Code Quality, Smells & Complexity Analysis.
  - **Slide 6**: Dependency Analysis & Configuration Hygiene.
  - **Slide 7**: Prioritized Remediation Roadmap (Phase 1 Immediate, Phase 2 Short-term, Phase 3 Excellence).
- Output: Valid `.pptx` binary (`PK\x03\x04` ZIP archive, ~38.6 KB).

---

## 7. Automated Test Verification Results

### 7.1 Backend & AI Service Tests (`pytest`)
- **Total Tests Executed:** 67
- **Passed:** 67
- **Failed:** 0
- **Exit Code:** 0
- **Execution Time:** 89.98s

Test breakdown:
- `tests/test_qwen_integration.py`: 10 passed (Missing key fallback, successful inference, 429 retry, 503 retry, timeout resilience, malformed JSON, secret scrubbing, transparent uncertainty, SSE streaming, PPTX presentation generation).
- `tests/test_rag_and_reports.py`: 7 passed.
- `tests/test_phase2_verification.py`: 15 passed.
- `tests/test_service_integration.py`: 11 passed.
- `tests/test_ai_service_api.py`: 5 passed.
- `tests/test_backend_api.py`: 5 passed.
- `tests/test_database_persistence.py`: 3 passed.
- `tests/test_redis_coordination.py`: 4 passed.
- `tests/test_ast_multilanguage_extended.py`: 4 passed.
- `tests/test_organizations_rbac.py`: 1 passed.
- `tests/test_webhooks.py`: 2 passed.

### 7.2 Frontend Tests (`vitest`)
- **Total Tests Executed:** 12
- **Passed:** 12
- **Failed:** 0
- **Exit Code:** 0
- **Execution Time:** 4.75s

### 7.3 Frontend Production Build (`vite build`)
- Transformed Modules: 2,470
- Output: `dist/index.html` (0.40 kB), CSS bundle (21.08 kB), JS chunks.
- Exit Code: 0

---

## 8. Startup Instructions

### Local Development:
```bash
# 1. Start AI Service (Port 8000)
cd ai-service
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 2. Start Main Backend (Port 8050)
cd ../backend
uvicorn app.main:app --host 0.0.0.0 --port 8050 --reload

# 3. Start Frontend (Port 5173)
cd ../frontend
npm run dev
```

### Docker Compose:
```bash
docker compose up -d
```
