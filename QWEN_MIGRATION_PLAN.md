# CodeSense AI — Migration Plan: Gemini to Qwen3-Coder-Next

**Document Version:** 1.0.0  
**Target Architecture:** Qwen/Qwen3-Coder-Next primary inference, Persistent Hybrid RAG, FastAPI Backend (8050), FastAPI AI Service (8000), ReportLab PDF & python-pptx PowerPoint generator, React/TypeScript/Vite Frontend.

---

## 1. Executive Summary & Objective

This plan details the end-to-end migration of CodeSense AI from Google Gemini to **Qwen3-Coder-Next** (`Qwen/Qwen3-Coder-Next`). 

Qwen3-Coder-Next will become the primary generative AI model across all intelligence capabilities:
1. **Repository-Aware AI Chatbot**: Grounded code queries with source citations.
2. **Code Review & Debugging**: AST-guided inspection and remediation.
3. **Bug & Code-Smell Explanations**: Detailed root-cause breakdown.
4. **Security Vulnerability Assessments**: In-depth mitigation strategies.
5. **Repository Architecture Analysis**: High-level structural overviews.
6. **Code Improvement Suggestions**: Production-grade diff and code patches.
7. **Automated PR Reviews**: Summaries, verdicts (`APPROVE`, `REQUEST_CHANGES`, `COMMENT`), inline review comments, and improvement roadmaps.
8. **PDF and PowerPoint Audit Report Explanations**: ReportLab PDF and `python-pptx` presentation generation.

---

## 2. Audit of Existing Gemini Integration

The audit identified the following components and dependencies tied to Gemini:

| Component | Location | Current Role | Migration Action |
| :--- | :--- | :--- | :--- |
| **LLM Adapter** | `ai-service/app/rag/llm_adapter.py` | `GeminiAdapter` calling `generativelanguage.googleapis.com` | Replace with `QwenAdapter` supporting OpenAI-compatible chat completions (`${QWEN_BASE_URL}/chat/completions`), token budgeting, streaming, and deterministic RAG fallback. |
| **Module Export** | `ai-service/app/rag/__init__.py` | Exports `gemini_adapter` | Export `qwen_adapter` (with backward-compatible alias). |
| **AI Service Entrypoint** | `ai-service/app/main.py` | `call_gemini()`, `/chat`, `/explain`, `/review/pr` | Replace `call_gemini` with `call_qwen()`; delegate to `qwen_adapter`. |
| **Vector Store Comments** | `ai-service/app/rag/vector_store.py` | Docstrings mentioning Gemini text-embedding | Update to generic local 256-dim projection / Qwen embeddings. |
| **Backend Configuration** | `backend/app/config.py` | `gemini_api_key` | Remove `gemini_api_key`; add `llm_provider`, `qwen_model`, `qwen_base_url`, `qwen_api_key`, `qwen_timeout`, `qwen_max_retries`, `qwen_max_output_tokens`. |
| **Reports Endpoints** | `backend/app/api/reports.py` | Supports PDF and Markdown downloads | Add PowerPoint (`pptx`) report format generation and authenticated downloads. |
| **Backend AI Client** | `backend/app/ai_client.py` | `generate_pdf_report()` | Add `generate_pptx_report()` calling `POST /reports/pptx`. |
| **PPTX Generator** | `ai-service/app/reports/pptx_generator.py` *(New)* | N/A | Implement 7-slide professional audit presentation generator using `python-pptx`. |
| **Frontend UI** | `frontend/src/components/Navbar.tsx`, `AuthLayout.tsx`, `Analysis.tsx` | References "Gemini AI Review Engine" | Update branding to "Qwen3-Coder-Next", update initial prompt, add PPTX download button. |
| **Deployment & Env** | `.env.example`, `docker-compose.yml`, `render.yaml`, `docs/deployment.md` | `GEMINI_API_KEY` | Update to `LLM_PROVIDER=qwen`, `QWEN_MODEL`, `QWEN_BASE_URL`, `QWEN_API_KEY`, etc. |
| **Test Suites** | `tests/test_gemini_integration.py`, `tests/test_rag_and_reports.py`, `tests/test_phase2_verification.py`, `tests/eval_rag_phase3.py` | Tests targeting `GeminiAdapter` | Replace with `test_qwen_integration.py` and update test assertions for Qwen. |

---

## 3. Qwen3-Coder-Next Integration Architecture

### 3.1 Environment Configuration
```env
LLM_PROVIDER=qwen
QWEN_MODEL=Qwen/Qwen3-Coder-Next
QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
QWEN_API_KEY=
QWEN_TIMEOUT=120
QWEN_MAX_RETRIES=2
QWEN_MAX_OUTPUT_TOKENS=1500
```

### 3.2 OpenAI-Compatible REST Protocol
Qwen models (hosted via DashScope, OpenRouter, vLLM, Ollama, HuggingFace Inference Endpoints, SiliconFlow) adhere to the standard OpenAI chat completions endpoint:
- **URL**: `${QWEN_BASE_URL}/chat/completions`
- **Headers**:
  - `Authorization: Bearer ${QWEN_API_KEY}`
  - `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "model": "Qwen/Qwen3-Coder-Next",
    "messages": [
      {"role": "system", "content": "<compact_system_prompt>"},
      {"role": "user", "content": "<grounded_user_prompt>"}
    ],
    "temperature": 0.2,
    "max_tokens": 1500,
    "stream": false
  }
  ```
- **Response Parsing**:
  - Content: `choices[0].message.content`
  - Usage Metrics: `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`

### 3.3 Reliability & Fallback Architecture
1. **Transient Error Resilience**: Exponential backoff on HTTP 429 (rate limits) and HTTP 500/502/503/504.
2. **Transparent Deterministic RAG Fallback**: If `QWEN_API_KEY` is not provided, is empty, or the endpoint encounters persistent outages, CodeSense transparently synthesizes responses from retrieved AST chunks and verified findings without hallucinating or breaking client communication.
3. **Secret Redaction**: Errors and debug messages scrub authorization headers and API tokens.

---

## 4. Multi-Format Report Generation Architecture

### 4.1 Server-Side PDF (ReportLab)
- Preserves existing two-pass `NumberedCanvas` ("Page X of Y").
- Generates `%PDF-1.4` binary streams with scorecard, breakdown, and remediation items.

### 4.2 Server-Side PowerPoint Presentation (`python-pptx`)
- Generates 16:9 widescreen presentation (`.pptx`):
  - **Slide 1**: Title, repository metadata, commit SHA, CodeSense AI badge.
  - **Slide 2**: Executive Summary, Maintainability Score card, Technical Debt Hours, Issue counts.
  - **Slide 3**: Architectural Overview & Tech Stack Breakdown.
  - **Slide 4**: Security Findings & CVE / Injection Vulnerability Matrix.
  - **Slide 5**: Code Quality & Complexity Smells (Nested loops, loose equality, etc.).
  - **Slide 6**: Dependency Analysis & Configuration Hygiene.
  - **Slide 7**: Prioritized Remediation Roadmap (Immediate, Short-term, Long-term).

---

## 5. Execution Stages

1. **Stage 1**: Implement `QwenAdapter` in `ai-service/app/rag/llm_adapter.py`.
2. **Stage 2**: Implement `python-pptx` report generator in `ai-service/app/reports/pptx_generator.py` and register routes.
3. **Stage 3**: Connect Backend routes in `backend/app/api/reports.py` and `backend/app/ai_client.py`.
4. **Stage 4**: Update Frontend UI components and add PPTX download trigger.
5. **Stage 5**: Build and run test suites: create `tests/test_qwen_integration.py` and verify all tests pass.
6. **Stage 6**: Remove all obsolete Gemini configurations, imports, and documentation.
7. **Stage 7**: Compile `QWEN_MIGRATION_REPORT.md` with verification proofs.
