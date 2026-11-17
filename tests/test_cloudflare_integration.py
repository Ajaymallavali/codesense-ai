import io
import json
import os
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch
import pytest

from app.rag.llm_adapter import (
    CloudflareWorkersAIAdapter,
    QwenAdapter,
    get_llm_adapter,
    redact_sensitive_str,
    cloudflare_adapter,
    qwen_adapter,
)


def make_mock_cloudflare_openai_response(
    text: str,
    model: str = "@cf/qwen/qwen2.5-coder-32b-instruct",
    prompt_tokens: int = 160,
    completion_tokens: int = 80,
    total_tokens: int = 240,
) -> MagicMock:
    """Mock OpenAI-compatible response from Cloudflare Workers AI."""
    payload = {
        "result": None,
        "success": True,
        "errors": [],
        "messages": [],
        "model": model,
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
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    return mock_resp


def make_mock_cloudflare_native_response(
    text: str,
    model: str = "@cf/qwen/qwen2.5-coder-32b-instruct",
) -> MagicMock:
    """Mock Cloudflare native response (result.response)."""
    payload = {
        "result": {
            "response": text,
        },
        "success": True,
        "errors": [],
        "messages": [],
        "model": model,
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    return mock_resp


def test_cloudflare_adapter_default_configuration():
    adapter = CloudflareWorkersAIAdapter()
    assert adapter.provider == "cloudflare"
    assert adapter.model == "@cf/qwen/qwen2.5-coder-32b-instruct"
    assert "alibaba/qwen-image-3.0-pro" not in adapter.model


def test_cloudflare_adapter_endpoint_construction():
    adapter = CloudflareWorkersAIAdapter(account_id="test_acc_12345", api_token="cfut_test_token")
    assert adapter.get_endpoint() == "https://api.cloudflare.com/client/v4/accounts/test_acc_12345/ai/v1/chat/completions"


def test_cloudflare_adapter_authorization_header():
    adapter = CloudflareWorkersAIAdapter(account_id="test_acc_12345", api_token="cfut_test_token_abcdef1234567890")
    req, payload = adapter._build_request([{"role": "user", "content": "hello"}])
    assert req.headers["Authorization"] == "Bearer cfut_test_token_abcdef1234567890"
    assert req.headers["Content-type"] == "application/json"
    assert payload["model"] == "@cf/qwen/qwen2.5-coder-32b-instruct"
    assert payload["messages"] == [{"role": "user", "content": "hello"}]


def test_cloudflare_adapter_missing_credentials_fallback():
    with patch.dict(os.environ, {"CLOUDFLARE_API_TOKEN": "", "CLOUDFLARE_ACCOUNT_ID": ""}, clear=True):
        adapter = CloudflareWorkersAIAdapter()
        assert not adapter.is_available()

        # Direct text completion without credentials raises ValueError
        with pytest.raises(ValueError, match="unconfigured or unavailable"):
            adapter.generate_text("Explain this function")

        # Grounded response falls back transparently to deterministic RAG engine
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
        assert len(res["citations"]) == 1
        assert res["citations"][0]["filePath"] == "src/billing.py"


def test_cloudflare_adapter_successful_response_openai_format():
    env_vars = {
        "CLOUDFLARE_API_TOKEN": "cfut_valid_test_token_1234567890",
        "CLOUDFLARE_ACCOUNT_ID": "acct_test_1234567890",
        "CLOUDFLARE_MODEL": "@cf/qwen/qwen2.5-coder-32b-instruct",
    }
    with patch.dict(os.environ, env_vars):
        adapter = CloudflareWorkersAIAdapter()
        assert adapter.is_available()

        mock_answer = (
            "The `calculate_sales_tax` function in `[src/billing.py:1-10]` computes sales tax at 8%.\n"
            "```python\ndef calculate_sales_tax(subtotal):\n    return subtotal * 0.08\n```"
        )
        mock_resp = make_mock_cloudflare_openai_response(mock_answer, prompt_tokens=140, completion_tokens=70, total_tokens=210)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = adapter.generate_grounded_response(
                query="How does calculate_sales_tax work?",
                repository_name="test/repo_alpha",
                branch="main",
                commit_sha="2471966e",
                context_block="<source_chunk file=\"src/billing.py\">def calculate_sales_tax(subtotal): return subtotal * 0.08</source_chunk>",
                citations=[{"filePath": "src/billing.py", "startLine": 1, "endLine": 10, "symbol": "calculate_sales_tax"}],
            )
            assert res["provider"] == "cloudflare"
            assert res["model"] == "@cf/qwen/qwen2.5-coder-32b-instruct"
            assert "calculate_sales_tax" in res["text"]
            assert res["usage"]["prompt_tokens"] == 140
            assert res["usage"]["completion_tokens"] == 70
            assert res["usage"]["total_tokens"] == 210
            assert len(res["citations"]) == 1


def test_cloudflare_adapter_successful_response_native_format():
    env_vars = {
        "CLOUDFLARE_API_TOKEN": "cfut_valid_test_token_1234567890",
        "CLOUDFLARE_ACCOUNT_ID": "acct_test_1234567890",
    }
    with patch.dict(os.environ, env_vars):
        adapter = CloudflareWorkersAIAdapter()
        mock_answer = "Analysis from Cloudflare native format."
        mock_resp = make_mock_cloudflare_native_response(mock_answer)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            text = adapter.generate_text("Summarize the project structure")
            assert text == "Analysis from Cloudflare native format."


def test_cloudflare_adapter_streaming_openai_format():
    env_vars = {
        "CLOUDFLARE_API_TOKEN": "cfut_valid_test_token_1234567890",
        "CLOUDFLARE_ACCOUNT_ID": "acct_test_1234567890",
    }
    with patch.dict(os.environ, env_vars):
        adapter = CloudflareWorkersAIAdapter()

        sse_lines = [
            b'data: {"choices": [{"delta": {"content": "Cloudflare"}}]}\n',
            b'data: {"choices": [{"delta": {"content": " Workers"}}]}\n',
            b'data: {"choices": [{"delta": {"content": " AI"}}]}\n',
            b'data: [DONE]\n',
        ]
        mock_resp = MagicMock()
        mock_resp.__iter__.return_value = iter(sse_lines)
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            stream_gen = adapter.generate_stream(
                query="Hello",
                repository_name="test/repo",
                branch="main",
                commit_sha="HEAD",
                context_block="dummy context",
                citations=[],
            )
            tokens = list(stream_gen)
            assert tokens == ["Cloudflare", " Workers", " AI"]


def test_cloudflare_adapter_streaming_native_format():
    env_vars = {
        "CLOUDFLARE_API_TOKEN": "cfut_valid_test_token_1234567890",
        "CLOUDFLARE_ACCOUNT_ID": "acct_test_1234567890",
    }
    with patch.dict(os.environ, env_vars):
        adapter = CloudflareWorkersAIAdapter()

        sse_lines = [
            b'data: {"response": "Tokens"}\n',
            b'data: {"response": " from"}\n',
            b'data: {"response": " native"}\n',
            b'data: [DONE]\n',
        ]
        mock_resp = MagicMock()
        mock_resp.__iter__.return_value = iter(sse_lines)
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            stream_gen = adapter.generate_stream(
                query="Hello",
                repository_name="test/repo",
                branch="main",
                commit_sha="HEAD",
                context_block="dummy context",
                citations=[],
            )
            tokens = list(stream_gen)
            assert tokens == ["Tokens", " from", " native"]


def test_cloudflare_adapter_rate_limit_retry():
    env_vars = {
        "CLOUDFLARE_API_TOKEN": "cfut_valid_test_token_1234567890",
        "CLOUDFLARE_ACCOUNT_ID": "acct_test_1234567890",
    }
    with patch.dict(os.environ, env_vars):
        adapter = CloudflareWorkersAIAdapter(max_retries=2)

        rate_limit_err = urllib.error.HTTPError(
            url="https://api.cloudflare.com/...",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=io.BytesIO(b'{"errors": [{"message": "Rate limit exceeded"}]}'),
        )
        success_resp = make_mock_cloudflare_openai_response("Recovered after Cloudflare rate limit retry")

        with patch("time.sleep", return_value=None):
            with patch("urllib.request.urlopen", side_effect=[rate_limit_err, success_resp]):
                res = adapter.generate_grounded_response(
                    query="Retry test",
                    repository_name="test/repo",
                    branch="main",
                    commit_sha="HEAD",
                    context_block="ctx",
                    citations=[],
                )
                assert res["provider"] == "cloudflare"
                assert "Recovered after Cloudflare rate limit retry" in res["text"]


def test_cloudflare_adapter_service_unavailable_retry_and_fallback():
    env_vars = {
        "CLOUDFLARE_API_TOKEN": "cfut_valid_test_token_1234567890",
        "CLOUDFLARE_ACCOUNT_ID": "acct_test_1234567890",
    }
    with patch.dict(os.environ, env_vars):
        adapter = CloudflareWorkersAIAdapter(max_retries=1)

        server_err = urllib.error.HTTPError(
            url="https://api.cloudflare.com/...",
            code=503,
            msg="Service Unavailable",
            hdrs={},
            fp=io.BytesIO(b'{"errors": [{"message": "Workers AI capacity temporarily exhausted"}]}'),
        )

        with patch("time.sleep", return_value=None):
            with patch("urllib.request.urlopen", side_effect=[server_err, server_err]):
                res = adapter.generate_grounded_response(
                    query="Fallback test",
                    repository_name="test/repo",
                    branch="main",
                    commit_sha="HEAD",
                    context_block="ctx",
                    citations=[{"filePath": "src/api.py", "startLine": 1, "endLine": 15, "symbol": "api"}],
                )
                assert res["provider"] == "deterministic-rag"
                assert "Cloudflare Workers AI inference endpoint unconfigured or unavailable" in res["text"]
                assert "deterministic" in res["text"].lower()
                assert len(res["citations"]) == 1


def test_cloudflare_adapter_no_secret_leak_in_errors():
    secret_token = "cfut_super_secret_cloudflare_token_abcdef1234567890"
    with patch.dict(os.environ, {"CLOUDFLARE_API_TOKEN": secret_token, "CLOUDFLARE_ACCOUNT_ID": "acct_123"}):
        adapter = CloudflareWorkersAIAdapter(max_retries=0)

        http_err = urllib.error.HTTPError(
            url="https://api.cloudflare.com/...",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(f'{{"errors": [{{"message": "Invalid token: Bearer {secret_token}"}}]}}'.encode("utf-8")),
        )

        with patch("urllib.request.urlopen", side_effect=http_err):
            with patch("app.rag.llm_adapter.logger.warning") as mock_log:
                res = adapter.generate_grounded_response(
                    query="Secret test",
                    repository_name="test/repo",
                    branch="main",
                    commit_sha="HEAD",
                    context_block="ctx",
                    citations=[],
                )
                assert res["provider"] == "deterministic-rag"
                # Verify logger was called and token was never logged in cleartext
                for call in mock_log.call_args_list:
                    log_args = str(call)
                    assert secret_token not in log_args
                    assert "[REDACTED_CLOUDFLARE_TOKEN]" in log_args or "[REDACTED]" in log_args


def test_redact_sensitive_str_cloudflare_token():
    sample_text = "Error connecting with token cfut_mock_test_token_abcdef1234567890 at runtime"
    cleaned = redact_sensitive_str(sample_text)
    assert "cfut_mock_test_token_abcdef1234567890" not in cleaned
    assert "[REDACTED_CLOUDFLARE_TOKEN]" in cleaned


def test_get_llm_adapter_provider_selection():
    with patch.dict(os.environ, {"LLM_PROVIDER": "cloudflare"}):
        adapter = get_llm_adapter()
        assert adapter.provider == "cloudflare"

    with patch.dict(os.environ, {"LLM_PROVIDER": "qwen"}):
        adapter = get_llm_adapter()
        assert adapter.provider == "qwen"

    # Explicit provider argument override
    adapter_cf = get_llm_adapter(provider="cloudflare")
    assert adapter_cf.provider == "cloudflare"

    adapter_qw = get_llm_adapter(provider="qwen")
    assert adapter_qw.provider == "qwen"


def test_cloudflare_adapter_multi_turn_history_injection():
    with patch.dict(
        os.environ,
        {
            "CLOUDFLARE_API_TOKEN": "cfut_test_mock_token_12345",
            "CLOUDFLARE_ACCOUNT_ID": "mock_acc_1234567890abcdef",
        },
    ):
        adapter = CloudflareWorkersAIAdapter()
        mock_resp = make_mock_cloudflare_openai_response(
            "Here is the refactored secure payment handler."
        )

        history = [
            {"role": "user", "content": "What does billing.py do?"},
            {"role": "assistant", "content": "It calculates sales tax."},
        ]

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            res = adapter.generate_grounded_response(
                query="How do I optimize calculate_sales_tax?",
                repository_name="test/repo",
                branch="main",
                commit_sha="HEAD",
                context_block="def calculate_sales_tax(subtotal, rate):\n    return subtotal * rate",
                citations=[],
                conversation_history=history,
            )

            assert res["text"] == "Here is the refactored secure payment handler."
            assert res["provider"] == "cloudflare"

            # Inspect intercepted Request payload
            assert mock_urlopen.call_count == 1
            called_req = mock_urlopen.call_args[0][0]
            req_body = json.loads(called_req.data.decode("utf-8"))
            msgs = req_body["messages"]

            # First message must be system prompt
            assert msgs[0]["role"] == "system"
            assert "Principal Staff Software Architect" in msgs[0]["content"]

            # Subsequent messages must include the history turns
            assert msgs[1]["role"] == "user"
            assert msgs[1]["content"] == "What does billing.py do?"
            assert msgs[2]["role"] == "assistant"
            assert msgs[2]["content"] == "It calculates sales tax."

            # Final message must be the grounded user query
            assert msgs[3]["role"] == "user"
            assert "How do I optimize calculate_sales_tax?" in msgs[3]["content"]
