import io
import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import urllib.error

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ai-service"))

from app.rag.llm_adapter import QwenAdapter, redact_sensitive_str


class TestStage1LiveQwen(unittest.TestCase):
    def test_default_configuration(self):
        """Verify default DashScope endpoint and Qwen3-Coder-Next model configuration."""
        adapter = QwenAdapter()
        self.assertEqual(adapter.model, "Qwen/Qwen3-Coder-Next")
        self.assertEqual(adapter.base_url, "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
        self.assertEqual(adapter.provider, "qwen")

    def test_missing_api_key_graceful_fallback(self):
        """When no key is configured, adapter safely falls back with citations."""
        with patch.dict(os.environ, {}, clear=True):
            if "QWEN_API_KEY" in os.environ:
                del os.environ["QWEN_API_KEY"]
            if "DASHSCOPE_API_KEY" in os.environ:
                del os.environ["DASHSCOPE_API_KEY"]
            adapter = QwenAdapter()
            self.assertFalse(adapter.is_available())

            citations = [{"filePath": "src/billing.py", "startLine": 1, "endLine": 10, "symbol": "tax"}]
            res = adapter.generate_grounded_response(
                query="What tax rate is used?",
                repository_name="test/repo",
                branch="main",
                commit_sha="c1",
                context_block="<source_chunk>def tax(): return 0.0825</source_chunk>",
                citations=citations,
            )
            self.assertEqual(res["provider"], "deterministic-rag")
            self.assertEqual(res["citations"], citations)
            self.assertIn("tax", res["text"])
            self.assertIn("Qwen3-Coder", res["text"])

    def test_live_dashscope_invalid_key_401(self):
        """Verify real network call to DashScope with invalid credentials returns 401 and redacts token."""
        test_fake_key = "sk-invalid-test-credential-xyz987"
        adapter = QwenAdapter(api_key=test_fake_key)
        self.assertTrue(adapter.is_available())

        citations = [{"filePath": "src/billing.py", "startLine": 1, "endLine": 10, "symbol": "tax"}]
        res = adapter.generate_grounded_response(
            query="What tax rate is used?",
            repository_name="test/repo",
            branch="main",
            commit_sha="c1",
            context_block="<source_chunk>def tax(): return 0.0825</source_chunk>",
            citations=citations,
        )

        # Confirm graceful degradation despite 401
        self.assertEqual(res["provider"], "deterministic-rag")
        self.assertEqual(res["citations"], citations)
        self.assertIn("tax", res["text"])

        # Confirm secret key scrubbing
        scrubbed = redact_sensitive_str(f"Authorization: Bearer {test_fake_key}")
        self.assertNotIn("xyz987", scrubbed)
        self.assertIn("[REDACTED]", scrubbed)

    def test_retry_on_429_and_503(self):
        """Verify retry logic on transient HTTP errors (429, 503)."""
        adapter = QwenAdapter(api_key="sk-dummy-key")
        attempt_count = 0

        def mock_urlopen(req, timeout):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                # First attempt: 429 Too Many Requests
                raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, io.BytesIO(b'{"error": "rate_limit"}'))
            # Second attempt: success
            mock_resp = MagicMock()
            mock_resp.__enter__.return_value = mock_resp
            mock_resp.read.return_value = json.dumps({
                "choices": [{"message": {"content": "Retry succeeded!"}}],
                "usage": {"prompt_tokens": 15, "completion_tokens": 5, "total_tokens": 20}
            }).encode("utf-8")
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            res = adapter.generate_grounded_response(
                query="Hello",
                repository_name="test/repo",
                branch="main",
                commit_sha="c1",
                context_block="chunk",
                citations=[],
            )
            self.assertEqual(res["text"], "Retry succeeded!")
            self.assertEqual(res["usage"]["total_tokens"], 20)
            self.assertEqual(attempt_count, 2)

    def test_successful_live_response_parsing_and_token_usage(self):
        """Verify successful response parsing extracts text, metadata and exact token usage."""
        adapter = QwenAdapter(api_key="sk-live-key")

        mock_payload = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "The calculate_sales_tax function uses an 8.25% state tax rate."
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 240,
                "completion_tokens": 45,
                "total_tokens": 285
            }
        }

        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = adapter.generate_grounded_response(
                query="What tax rate is used in billing?",
                repository_name="test/repo",
                branch="main",
                commit_sha="c1",
                context_block="<source_chunk>def calculate_sales_tax(amount): return round(amount * 0.0825, 2)</source_chunk>",
                citations=[{"filePath": "src/billing.py", "startLine": 1, "endLine": 5}],
            )
            self.assertEqual(res["provider"], "qwen")
            self.assertEqual(res["model"], "Qwen/Qwen3-Coder-Next")
            self.assertIn("8.25%", res["text"])
            self.assertEqual(res["usage"]["prompt_tokens"], 240)
            self.assertEqual(res["usage"]["completion_tokens"], 45)
            self.assertEqual(res["usage"]["total_tokens"], 285)

    def test_streaming_sse_generation(self):
        """Verify SSE streaming yields individual token fragments."""
        adapter = QwenAdapter(api_key="sk-live-key")

        sse_stream = [
            b'data: {"choices": [{"delta": {"content": "Hello"}}]}\n',
            b'data: {"choices": [{"delta": {"content": " world"}}]}\n',
            b'data: {"choices": [{"delta": {"content": "!"}}]}\n',
            b'data: [DONE]\n'
        ]

        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__iter__.return_value = iter(sse_stream)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            generator = adapter.generate_stream(
                query="Greet",
                repository_name="test/repo",
                branch="main",
                commit_sha="c1",
                context_block="dummy context",
                citations=[],
            )
            tokens = list(generator)
            self.assertEqual(tokens, ["Hello", " world", "!"])


if __name__ == "__main__":
    unittest.main()
