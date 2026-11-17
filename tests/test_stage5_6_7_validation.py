import io
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ai-service"))
sys.path.insert(0, str(ROOT / "backend"))
import app
ai_app_path = str(ROOT / "ai-service" / "app")
if ai_app_path not in app.__path__:
    app.__path__.append(ai_app_path)

from app.reports.pdf_generator import pdf_report_generator
from app.reports.pptx_generator import pptx_report_generator
from app.rag.llm_adapter import redact_sensitive_str, QwenAdapter
from app.rag.retriever import HybridRetriever, Citation
from app.rag.vector_store import PersistentVectorStore


class TestStage5ChatbotExperience(unittest.TestCase):
    def test_multi_turn_citations_and_grounding(self):
        """Verify multi-turn conversation maintains citations and grounded response structure."""
        adapter = QwenAdapter()
        citations = [
            {"filePath": "src/OrderService.java", "startLine": 15, "endLine": 35, "symbol": "calculateOrderTotal"},
            {"filePath": "pom.xml", "startLine": 1, "endLine": 20, "symbol": "dependencies"},
        ]
        context = (
            "<source_chunk file=\"src/OrderService.java\" lines=\"15-35\" symbol=\"calculateOrderTotal\">\n"
            "public BigDecimal calculateOrderTotal(Order order, double taxRate) {\n"
            "    BigDecimal subtotal = order.getSubtotal();\n"
            "    return subtotal.multiply(BigDecimal.valueOf(1 + taxRate));\n"
            "}\n"
            "</source_chunk>"
        )

        # Turn 1
        res1 = adapter.generate_grounded_response(
            query="Where is calculateOrderTotal defined?",
            repository_name="test/repo_gamma",
            branch="main",
            commit_sha="c1",
            context_block=context,
            citations=citations,
        )
        self.assertIn("calculateOrderTotal", res1["text"])
        self.assertEqual(len(res1["citations"]), 2)

        # Turn 2 with conversation context
        turn2_instruction = "In previous turn developer asked about calculateOrderTotal. Answer follow-up query."
        res2 = adapter.generate_grounded_response(
            query="What parameters does calculateOrderTotal accept?",
            repository_name="test/repo_gamma",
            branch="main",
            commit_sha="c1",
            context_block=context,
            citations=citations,
            system_instruction=turn2_instruction,
        )
        self.assertIn("calculateOrderTotal", res2["text"])
        self.assertEqual(res2["citations"][0]["filePath"], "src/OrderService.java")

    def test_streaming_token_delivery(self):
        """Verify SSE streaming yields valid string tokens and completes cleanly."""
        adapter = QwenAdapter()
        context = "<source_chunk file=\"src/server.ts\" lines=\"1-10\" symbol=\"server\">app.listen(3000);</source_chunk>"
        citations = [{"filePath": "src/server.ts", "startLine": 1, "endLine": 10, "symbol": "server"}]

        stream = adapter.generate_stream(
            query="What port does server listen on?",
            repository_name="test/repo_delta",
            branch="main",
            commit_sha="c1",
            context_block=context,
            citations=citations,
        )
        tokens = list(stream)
        self.assertGreater(len(tokens), 0)
        full_text = "".join(tokens)
        self.assertIn("server", full_text.lower())


class TestStage6ReportGeneration(unittest.TestCase):
    def test_pdf_generation_java_spring(self):
        """Verify PDF report generation for Java Spring Boot repository."""
        data = {
            "repository": "test/repo_gamma",
            "branch": "main",
            "commit_sha": "a1b2c3d4",
            "maintainability_score": 82,
            "technical_debt_hours": 14,
            "architecture": "Spring Boot (Java) with JPA",
            "findings": [
                {
                    "category": "Security",
                    "title": "Insecure Deserialization in JwtAuthFilter",
                    "severity": "High",
                    "file": "src/main/java/com/codesense/commerce/security/JwtAuthFilter.java",
                    "line_number": 42,
                    "suggestion": "Replace ObjectInputStream with a safe JSON claims parser.",
                },
                {
                    "category": "Code smell",
                    "title": "Duplicated database query in OrderRepository",
                    "severity": "Medium",
                    "file": "src/main/java/com/codesense/commerce/repository/OrderRepository.java",
                    "line_number": 19,
                    "suggestion": "Consolidate custom queries into shared repository interface method.",
                },
            ],
        }
        pdf_bytes = pdf_report_generator.generate(data)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-1.4"))
        self.assertGreater(len(pdf_bytes), 3000)

    def test_pptx_generation_node_sql(self):
        """Verify 16:9 widescreen PPTX generation for Node.js Express SQL repository."""
        data = {
            "repository": "test/repo_delta",
            "branch": "main",
            "commit_sha": "e5f6g7h8",
            "maintainability_score": 91,
            "technical_debt_hours": 6,
            "architecture": "Node.js Express with PostgreSQL",
            "findings": [
                {
                    "category": "Security",
                    "title": "Unparameterized LIKE query in user search",
                    "severity": "High",
                    "file": "src/routes/users.ts",
                    "line_number": 28,
                    "suggestion": "Use PostgreSQL parameterized placeholder ($1) instead of template strings.",
                },
                {
                    "category": "Complexity",
                    "title": "Elevated complexity in billing invoice calculation",
                    "severity": "Medium",
                    "file": "src/services/billingService.ts",
                    "line_number": 45,
                    "suggestion": "Break invoice calculation down into subtotal and tax calculation functions.",
                },
            ],
        }
        pptx_bytes = pptx_report_generator.generate(data)
        self.assertTrue(pptx_bytes.startswith(b"PK\x03\x04"))
        self.assertGreater(len(pptx_bytes), 20000)


class TestStage7OperationalReadiness(unittest.TestCase):
    def test_safe_secret_logging_redaction(self):
        """Verify passwords, GitHub PATs, and Qwen API keys are never leaked in logs."""
        raw_log = "Error connecting with Authorization: Bearer sk-d87f6a5b4c3e2d1a and GITHUB_TOKEN ghp_1234567890abcdef1234567890abcdef1234"
        scrubbed = redact_sensitive_str(raw_log)
        self.assertNotIn("sk-d87f6a5b4c3e2d1a", scrubbed)
        self.assertNotIn("ghp_1234567890abcdef1234567890abcdef1234", scrubbed)
        self.assertIn("[REDACTED]", scrubbed)

    def test_docker_compose_config_structure(self):
        """Verify docker-compose.yml defines required postgres, redis, backend, and ai-service containers."""
        dc_path = ROOT / "docker-compose.yml"
        self.assertTrue(dc_path.exists())
        content = dc_path.read_text(encoding="utf-8")
        self.assertIn("postgres:", content)
        self.assertIn("redis:", content)
        self.assertIn("backend:", content)
        self.assertIn("ai-service:", content)


if __name__ == "__main__":
    unittest.main()
