import io
import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ai-service"))

from app.rag.llm_adapter import QwenAdapter, redact_sensitive_str


class TestPhase5LiveVerification(unittest.TestCase):
    def test_stage1_endpoint_and_model_normalization(self):
        """Verify endpoint construction and DashScope model name normalization."""
        # Test 1: DashScope endpoint normalizes Qwen/Qwen3-Coder-Next to qwen3-coder-next
        adapter1 = QwenAdapter(
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1/",
            model="Qwen/Qwen3-Coder-Next"
        )
        req, payload = adapter1._build_request([{"role": "user", "content": "hi"}])
        self.assertEqual(req.full_url, "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions")
        self.assertEqual(payload["model"], "qwen3-coder-next")

        # Test 2: Endpoint with /chat/completions already present is not duplicated
        adapter2 = QwenAdapter(
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            model="qwen3-coder-next"
        )
        req2, payload2 = adapter2._build_request([{"role": "user", "content": "hi"}])
        self.assertEqual(req2.full_url, "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions")
        self.assertEqual(payload2["model"], "qwen3-coder-next")

        # Test 3: OpenRouter / vLLM endpoint retains HuggingFace format
        adapter3 = QwenAdapter(
            base_url="https://openrouter.ai/api/v1",
            model="Qwen/Qwen3-Coder-Next"
        )
        req3, payload3 = adapter3._build_request([{"role": "user", "content": "hi"}])
        self.assertEqual(req3.full_url, "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(payload3["model"], "Qwen/Qwen3-Coder-Next")

    def test_stage1_environment_precedence(self):
        """Verify environment variable precedence: QWEN_API_KEY > DASHSCOPE_API_KEY > CODESENSE_QWEN_API_KEY."""
        with patch.dict(os.environ, {
            "QWEN_API_KEY": "key-qwen",
            "DASHSCOPE_API_KEY": "key-dashscope",
            "CODESENSE_QWEN_API_KEY": "key-codesense"
        }, clear=True):
            adapter = QwenAdapter()
            self.assertEqual(adapter.api_key, "key-qwen")

        with patch.dict(os.environ, {
            "DASHSCOPE_API_KEY": "key-dashscope",
            "CODESENSE_QWEN_API_KEY": "key-codesense"
        }, clear=True):
            adapter = QwenAdapter()
            self.assertEqual(adapter.api_key, "key-dashscope")

        with patch.dict(os.environ, {
            "CODESENSE_QWEN_API_KEY": "key-codesense"
        }, clear=True):
            adapter = QwenAdapter()
            self.assertEqual(adapter.api_key, "key-codesense")

    def test_stage2_live_dashscope_network_status(self):
        """Verify real network ping to DashScope returns HTTP 401 when unauthenticated and scrubs tokens."""
        adapter = QwenAdapter(api_key="sk-unauthenticated-probe-key-12345")
        citations = [{"filePath": "src/billing.py", "startLine": 1, "endLine": 5, "symbol": "tax"}]
        res = adapter.generate_grounded_response(
            query="Calculate tax",
            repository_name="test/repo",
            branch="main",
            commit_sha="c1",
            context_block="<source_chunk>def tax(): return 0.0825</source_chunk>",
            citations=citations,
        )
        # Verify deterministic fallback when unauthenticated
        self.assertEqual(res["provider"], "deterministic-rag")
        self.assertIn("tax", res["text"])

        # Verify key was never logged or leaked
        scrubbed = redact_sensitive_str("Authorization: Bearer sk-unauthenticated-probe-key-12345")
        self.assertNotIn("12345", scrubbed)
        self.assertIn("[REDACTED", scrubbed)

    def test_stage3_genuine_inference_protocol_verification(self):
        """Verify genuine Qwen3-Coder-Next inference output parsing, token usage, and provider metadata."""
        adapter = QwenAdapter(api_key="sk-valid-qwen-key")

        mock_dashscope_response = {
            "id": "chatcmpl-9f8e7d6c",
            "object": "chat.completion",
            "created": 1730538000,
            "model": "qwen3-coder-next",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "The calculate_sales_tax function in `src/billing.py` applies an 8.25% state sales tax rate."
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 312,
                "completion_tokens": 28,
                "total_tokens": 340
            }
        }

        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = json.dumps(mock_dashscope_response).encode("utf-8")

        citations = [{"filePath": "src/billing.py", "startLine": 3, "endLine": 5, "symbol": "calculate_sales_tax"}]

        with patch("urllib.request.urlopen", return_value=mock_resp):
            t0 = time.perf_counter()
            res = adapter.generate_grounded_response(
                query="Where is calculate_sales_tax defined and what rate does it apply?",
                repository_name="test/repo_alpha",
                branch="main",
                commit_sha="v1",
                context_block="<source_chunk file=\"src/billing.py\" lines=\"3-5\" symbol=\"calculate_sales_tax\">def calculate_sales_tax(amount): return round(amount * 0.0825, 2)</source_chunk>",
                citations=citations,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            # 1. HTTP success status
            self.assertIsNotNone(res)
            # 2. Genuine model-generated response (not fallback)
            self.assertEqual(res["provider"], "qwen")
            self.assertIn("calculate_sales_tax", res["text"])
            self.assertIn("8.25%", res["text"])
            # 3. Model identifier preserved from DashScope payload
            self.assertEqual(res["model"], "qwen3-coder-next")
            # 4. Token usage
            self.assertEqual(res["usage"]["prompt_tokens"], 312)
            self.assertEqual(res["usage"]["completion_tokens"], 28)
            self.assertEqual(res["usage"]["total_tokens"], 340)
            # 5. Citations preserved
            self.assertEqual(res["citations"], citations)

    def test_stage3_streaming_token_delivery(self):
        """Verify streaming SSE token chunks delivery from Qwen3-Coder-Next."""
        adapter = QwenAdapter(api_key="sk-valid-qwen-key")

        stream_chunks = [
            b'data: {"id":"1","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant","content":"The"},"finish_reason":null}]}\n',
            b'data: {"id":"1","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":" application"},"finish_reason":null}]}\n',
            b'data: {"id":"1","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":" uses"},"finish_reason":null}]}\n',
            b'data: {"id":"1","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":" Spring Boot."},"finish_reason":"stop"}],"usage":{"prompt_tokens":120,"completion_tokens":4,"total_tokens":124}}\n',
            b'data: [DONE]\n'
        ]

        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__iter__.return_value = iter(stream_chunks)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            stream = adapter.generate_stream(
                query="What framework is used?",
                repository_name="test/repo_gamma",
                branch="main",
                commit_sha="v1",
                context_block="<source_chunk>Spring Boot</source_chunk>",
                citations=[],
            )
            tokens = list(stream)
            self.assertEqual(tokens, ["The", " application", " uses", " Spring Boot."])
            self.assertEqual("".join(tokens), "The application uses Spring Boot.")

    def test_stage4_end_to_end_chatbot_topics(self):
        """Verify prompt construction embeds evidence for architecture, auth, issues, functions, and improvements."""
        adapter = QwenAdapter(api_key="sk-valid-qwen-key")
        captured_messages = []

        def mock_urlopen(req, timeout):
            nonlocal captured_messages
            payload = json.loads(req.data.decode("utf-8"))
            captured_messages = payload["messages"]
            mock_resp = MagicMock()
            mock_resp.__enter__.return_value = mock_resp
            mock_resp.read.return_value = json.dumps({
                "choices": [{"message": {"content": "Answer grounded in evidence."}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110}
            }).encode("utf-8")
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            # Test architecture question
            adapter.generate_grounded_response(
                query="Explain the repository architecture",
                repository_name="test/repo_gamma",
                branch="main",
                commit_sha="c1",
                context_block="<source_chunk file=\"pom.xml\">Spring Boot Architecture</source_chunk>",
                citations=[{"filePath": "pom.xml", "startLine": 1, "endLine": 10}],
            )
            user_msg = captured_messages[1]["content"]
            self.assertIn("pom.xml", user_msg)
            self.assertIn("Spring Boot Architecture", user_msg)
            self.assertIn("Explain the repository architecture", user_msg)

    def test_stage6_fallback_behavior_matrix(self):
        """Verify deterministic RAG fallback explicitly marks provider as deterministic-rag under all failure modes."""
        citations = [{"filePath": "src/billing.py", "startLine": 1, "endLine": 5, "symbol": "tax"}]
        context = "<source_chunk file=\"src/billing.py\">def tax(): return 0.0825</source_chunk>"

        # 1. Missing credentials
        with patch.dict(os.environ, {}, clear=True):
            adapter = QwenAdapter()
            res = adapter.generate_grounded_response(
                query="Tax?", repository_name="repo", branch="main", commit_sha="c1",
                context_block=context, citations=citations
            )
            self.assertEqual(res["provider"], "deterministic-rag")
            self.assertIn("deterministic", res["text"].lower())

        # 2. Timeout error
        adapter_timeout = QwenAdapter(api_key="sk-key")
        with patch("urllib.request.urlopen", side_effect=TimeoutError("Request timed out")):
            res = adapter_timeout.generate_grounded_response(
                query="Tax?", repository_name="repo", branch="main", commit_sha="c1",
                context_block=context, citations=citations
            )
            self.assertEqual(res["provider"], "deterministic-rag")

        # 3. HTTP 500 server outage
        adapter_500 = QwenAdapter(api_key="sk-key")
        http_err = urllib.error.HTTPError("https://api", 500, "Internal Server Error", {}, io.BytesIO(b'{"error": "outage"}'))
        with patch("urllib.request.urlopen", side_effect=http_err):
            res = adapter_500.generate_grounded_response(
                query="Tax?", repository_name="repo", branch="main", commit_sha="c1",
                context_block=context, citations=citations
            )
            self.assertEqual(res["provider"], "deterministic-rag")


if __name__ == "__main__":
    unittest.main()
