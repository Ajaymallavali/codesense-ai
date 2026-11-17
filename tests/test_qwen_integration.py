import io
import json
import os
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch
import pytest

from app.rag.llm_adapter import QwenAdapter
from app.reports.pptx_generator import PptxAuditReportGenerator


def make_mock_qwen_response(
    text: str,
    prompt_tokens: int = 150,
    completion_tokens: int = 75,
    total_tokens: int = 225,
) -> MagicMock:
    response_payload = {
        "id": "chatcmpl-qwen-test-12345",
        "object": "chat.completion",
        "created": 1730000000,
        "model": "Qwen/Qwen3-Coder-Next",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": text,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
    }
    raw_bytes = json.dumps(response_payload).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = raw_bytes
    mock_resp.__enter__.return_value = mock_resp
    return mock_resp


def test_qwen_adapter_missing_api_key():
    with patch.dict(os.environ, {}, clear=True):
        adapter = QwenAdapter()
        assert not adapter.is_available()

        # Direct text completion without key raises ValueError
        with pytest.raises(ValueError, match="unconfigured or unavailable"):
            adapter.generate_text("Explain this code")

        # Grounded response falls back to deterministic RAG engine
        res = adapter.generate_grounded_response(
            query="What does calculate_sales_tax do?",
            repository_name="test/repo_alpha",
            branch="main",
            commit_sha="2471966e",
            context_block="<source_chunk file=\"src/billing.py\">def calculate_sales_tax(subtotal): return subtotal * 0.08</source_chunk>",
            citations=[{"filePath": "src/billing.py", "startLine": 1, "endLine": 10, "symbol": "calculate_sales_tax"}],
        )
        assert res["provider"] == "deterministic-rag"
        assert "> [!NOTE]" in res["text"]
        assert "Deterministic Rule/RAG Response" in res["text"]


def test_qwen_adapter_successful_response():
    with patch.dict(os.environ, {"QWEN_API_KEY": "sk-qwen-test-key-12345"}):
        adapter = QwenAdapter()
        assert adapter.is_available()

        mock_answer = "The `calculate_sales_tax` function in `[src/billing.py:1-10]` calculates an 8% sales tax on the given subtotal."

        with patch("urllib.request.urlopen", return_value=make_mock_qwen_response(mock_answer)):
            res = adapter.generate_grounded_response(
                query="What does calculate_sales_tax do?",
                repository_name="test/repo_alpha",
                branch="main",
                commit_sha="2471966e",
                context_block="<source_chunk file=\"src/billing.py\">def calculate_sales_tax(subtotal): return subtotal * 0.08</source_chunk>",
                citations=[{"filePath": "src/billing.py", "startLine": 1, "endLine": 10, "symbol": "calculate_sales_tax"}],
            )

            assert res["provider"] == "qwen"
            assert res["model"] == "Qwen/Qwen3-Coder-Next"
            assert res["text"] == mock_answer
            assert len(res["citations"]) == 1
            assert res["citations"][0]["filePath"] == "src/billing.py"
            assert "usage" in res
            assert res["usage"]["total_tokens"] == 225
            assert "latency_ms" in res


def test_qwen_adapter_rate_limit_retry():
    with patch.dict(os.environ, {"QWEN_API_KEY": "sk-qwen-test-key-12345"}):
        adapter = QwenAdapter(max_retries=2)

        # First call fails with 429, second succeeds
        rate_limit_err = urllib.error.HTTPError(
            url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=io.BytesIO(b'{"error": {"message": "Rate limit exceeded"}}'),
        )
        success_resp = make_mock_qwen_response("Recovered after rate limit retry")

        with patch("urllib.request.urlopen", side_effect=[rate_limit_err, success_resp]):
            with patch("time.sleep", return_value=None) as mock_sleep:
                output = adapter.generate_text("Explain retry mechanism")
                assert output == "Recovered after rate limit retry"
                assert mock_sleep.call_count == 1


def test_qwen_adapter_service_unavailable_retry_and_fallback():
    with patch.dict(os.environ, {"QWEN_API_KEY": "sk-qwen-test-key-12345"}):
        adapter = QwenAdapter(max_retries=1)

        err_503 = urllib.error.HTTPError(
            url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            code=503,
            msg="Service Unavailable",
            hdrs={},
            fp=io.BytesIO(b'{"error": {"message": "Inference server overloaded"}}'),
        )

        with patch("urllib.request.urlopen", side_effect=[err_503, err_503]):
            with patch("time.sleep", return_value=None):
                # When all retries fail during grounded response, falls back gracefully to deterministic RAG
                res = adapter.generate_grounded_response(
                    query="Explain database structure",
                    repository_name="test/repo_alpha",
                    branch="main",
                    commit_sha="2471966e",
                    context_block="<source_chunk file=\"src/database.py\">cursor.execute()</source_chunk>",
                    citations=[{"filePath": "src/database.py", "startLine": 1, "endLine": 15, "symbol": "query"}],
                )
                assert res["provider"] == "deterministic-rag"
                assert "src/database.py" in res["text"]


def test_qwen_adapter_timeout_resilience():
    with patch.dict(os.environ, {"QWEN_API_KEY": "sk-qwen-test-key-12345"}):
        adapter = QwenAdapter(timeout_seconds=0.1, max_retries=0)

        with patch("urllib.request.urlopen", side_effect=TimeoutError("Request timed out")):
            res = adapter.generate_grounded_response(
                query="Architecture overview",
                repository_name="test/repo_alpha",
                branch="main",
                commit_sha="2471966e",
                context_block="README doc",
                citations=[],
            )
            assert res["provider"] == "deterministic-rag"


def test_qwen_adapter_malformed_json_response():
    with patch.dict(os.environ, {"QWEN_API_KEY": "sk-qwen-test-key-12345"}):
        adapter = QwenAdapter(max_retries=0)
        malformed_resp = MagicMock()
        malformed_resp.read.return_value = b"{not-valid-json"
        malformed_resp.__enter__.return_value = malformed_resp

        with patch("urllib.request.urlopen", return_value=malformed_resp):
            res = adapter.generate_grounded_response(
                query="Explain something",
                repository_name="test/repo_alpha",
                branch="main",
                commit_sha="2471966e",
                context_block="",
                citations=[],
            )
            assert res["provider"] == "deterministic-rag"


def test_qwen_adapter_no_secret_leak_in_errors():
    secret_key = "sk-qwen-super-secret-key-99999"
    with patch.dict(os.environ, {"QWEN_API_KEY": secret_key}):
        adapter = QwenAdapter(max_retries=0)

        http_err = urllib.error.HTTPError(
            url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(b'{"error": {"message": "Invalid API key provided: Bearer sk-qwen-super-secret-key-99999"}}'),
        )

        with patch("urllib.request.urlopen", side_effect=http_err):
            with pytest.raises(RuntimeError) as exc_info:
                adapter.generate_text("test")
            # Verify the secret key is NOT leaked in the raised error
            assert secret_key not in str(exc_info.value)
            assert "HTTP 401" in str(exc_info.value)


def test_qwen_adapter_transparent_uncertainty_for_missing_evidence():
    with patch.dict(os.environ, {}, clear=True):
        adapter = QwenAdapter()

        res = adapter.generate_grounded_response(
            query="Where is the Kubernetes Helm deployment and GraphQL schema?",
            repository_name="test/repo_alpha",
            branch="main",
            commit_sha="2471966e",
            context_block="<source_chunk file=\"src/billing.py\">def calculate_sales_tax(): pass</source_chunk>",
            citations=[{"filePath": "src/billing.py", "startLine": 1, "endLine": 10, "symbol": "calculate_sales_tax"}],
        )

        assert "Transparent Verification Status" in res["text"]
        assert "No evidence of" in res["text"]
        assert "kubernetes" in res["text"].lower() or "graphql" in res["text"].lower()


def test_qwen_adapter_streaming():
    with patch.dict(os.environ, {"QWEN_API_KEY": "sk-qwen-test-key-12345"}):
        adapter = QwenAdapter()

        # Mock SSE streaming response lines
        sse_lines = [
            b'data: {"choices": [{"delta": {"content": "Qwen3"}}]}\n',
            b'data: {"choices": [{"delta": {"content": "-Coder"}}]}\n',
            b'data: {"choices": [{"delta": {"content": " streaming."}}]}\n',
            b'data: [DONE]\n',
        ]
        mock_resp = MagicMock()
        mock_resp.__iter__.return_value = iter(sse_lines)
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            stream_gen = adapter.generate_stream(
                query="Stream test",
                repository_name="test/repo",
                branch="main",
                commit_sha="123456",
                context_block="code",
                citations=[],
            )
            tokens = list(stream_gen)
            assert "".join(tokens) == "Qwen3-Coder streaming."


def test_qwen_pptx_audit_report_generation():
    generator = PptxAuditReportGenerator()
    data = {
        "repository": "facebook/react",
        "branch": "main",
        "commit_sha": "a1b2c3d4e5f6",
        "maintainability_score": 94,
        "technical_debt_hours": 3,
        "architecture": "Modern Component UI Architecture",
        "findings": [
            {
                "category": "Security",
                "severity": "High",
                "file": "packages/react-dom/src/client.js",
                "line_number": 42,
                "title": "Cross-Site Scripting (XSS) risk via dangerouslySetInnerHTML",
                "suggestion": "Sanitize innerHTML with DOMPurify.",
            },
            {
                "category": "Complexity",
                "severity": "Medium",
                "file": "packages/react-reconciler/src/fiber.js",
                "line_number": 128,
                "title": "Deeply nested iteration in reconcileChildren",
                "suggestion": "Decompose reconciliation loop into helper functions.",
            },
        ],
    }
    pptx_bytes = generator.generate(data)
    assert isinstance(pptx_bytes, bytes)
    assert len(pptx_bytes) > 2000
    # ZIP PK magic header for PPTX
    assert pptx_bytes[:4] == b"PK\x03\x04"
