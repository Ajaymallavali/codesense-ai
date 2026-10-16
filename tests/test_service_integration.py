import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent

# Load backend/app
sys.path.insert(0, str(ROOT / "backend"))

import httpx
from app.ai_client import AiClient
from app.schemas import (
    AnalysisResponse,
    AiChatRequest,
    AiExplainRequest,
    GoogleAuthRequest,
    GitHubCallbackRequest,
    PrInlineComment,
    PrReviewRequest,
    PrReviewResponse,
)
from app.jobs import check_redis_health
from app.github_service import github_service
from app.oauth import verify_google_id_token, GoogleVerificationError

# Load ai-service/app/main.py explicitly to avoid package namespace collision
ai_main_path = ROOT / "ai-service" / "app" / "main.py"
spec = importlib.util.spec_from_file_location("ai_service_main", str(ai_main_path))
ai_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai_module)
ai_fastapi_app = ai_module.app


class TestServiceIntegration(unittest.TestCase):
    def setUp(self):
        self.ai_app = ai_fastapi_app
        # Initialize client with ASGITransport for in-memory testing
        transport = httpx.ASGITransport(app=self.ai_app)
        self.mock_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")

    def test_redis_health_fallback(self):
        """Verify Redis check returns graceful fallback when offline."""
        health = check_redis_health()
        self.assertIn("status", health)
        print("Redis Health Status:", health)

    def test_schemas(self):
        """Verify AnalysisResponse supports progress, errorMessage, and status transitions."""
        resp = AnalysisResponse(
            id=uuid4(),
            repositoryId=uuid4(),
            branch="main",
            maintainabilityScore=0,
            technicalDebtHours=0,
            status="PENDING",
            progress=5,
            startedAt="2026-10-15T12:00:00Z"
        )
        self.assertEqual(resp.status, "PENDING")
        self.assertEqual(resp.progress, 5)

        # Transition to SCANNING
        resp_scanning = AnalysisResponse(
            id=resp.id,
            repositoryId=resp.repositoryId,
            branch=resp.branch,
            maintainabilityScore=0,
            technicalDebtHours=0,
            status="SCANNING",
            progress=35,
            startedAt=resp.startedAt
        )
        self.assertEqual(resp_scanning.status, "SCANNING")
        self.assertEqual(resp_scanning.progress, 35)

        # Transition to COMPLETED
        resp_completed = AnalysisResponse(
            id=resp.id,
            repositoryId=resp.repositoryId,
            branch=resp.branch,
            maintainabilityScore=88,
            technicalDebtHours=14,
            status="COMPLETED",
            progress=100,
            startedAt=resp.startedAt
        )
        self.assertEqual(resp_completed.status, "COMPLETED")
        self.assertEqual(resp_completed.maintainabilityScore, 88)

    def test_github_oauth_url(self):
        """Verify GitHub OAuth authorize URL generation."""
        url_info = github_service.get_authorization_url(state="test_state_123")
        self.assertIn("url", url_info)
        self.assertIn("configured", url_info)
        print("GitHub OAuth URL generation:", url_info)

    def test_github_repository_branches_and_details(self):
        """Verify GitHub REST API branch listing and repository details."""
        async def _run():
            # Test details lookup
            details = await github_service.get_repository_details("pallets/flask")
            self.assertIn("name", details)
            self.assertIn("fullName", details)
            print("GitHub Repo Details (pallets/flask):", details["name"], "| default branch:", details["defaultBranch"])

            # Test branch listing
            branches = await github_service.get_repository_branches("pallets/flask")
            self.assertIsInstance(branches, list)
            self.assertGreater(len(branches), 0)
            print(f"GitHub Branches (pallets/flask): {branches[:3]} (total {len(branches)} branches)")

            # Test repository listing fallback/lookup
            repos = await github_service.list_user_repositories(access_token=None, username="demo")
            self.assertIsInstance(repos, list)
            self.assertGreater(len(repos), 0)
            print(f"User Repositories listed: {len(repos)} repos")

        asyncio.run(_run())

    def test_google_oauth_server_verification(self):
        """Verify server-side Google token verification logic."""
        async def _run():
            # 1. Dev mock token verification
            dev_user = await verify_google_id_token("mock-google-token")
            self.assertEqual(dev_user["email"], "demo.user@example.com")
            self.assertEqual(dev_user["displayName"], "Google Demo User")
            print("Google OAuth Dev Token Verification: PASSED (demo.user@example.com)")

            # 2. Reject empty token
            with self.assertRaises(GoogleVerificationError):
                await verify_google_id_token("")

            # 3. Reject invalid forged token
            with self.assertRaises(GoogleVerificationError):
                await verify_google_id_token("forged.fake.jwt.token.12345")
            print("Google OAuth Forged Token Rejection: PASSED (HTTP 401 rejected)")

        asyncio.run(_run())

    def test_pr_review_schemas(self):
        """Verify PrReviewRequest and PrReviewResponse serialization & schema defaults."""
        req = PrReviewRequest(
            repositoryId=uuid4(),
            branch="feature/auth-patch",
            prTitle="Fix JWT hardcoded secrets",
            diff="--- a/app/auth.py\n+++ b/app/auth.py\n@@ -10 +10 @@\n-SECRET = 'default'\n+SECRET = os.getenv('JWT_SECRET')"
        )
        self.assertEqual(req.branch, "feature/auth-patch")
        self.assertIn("SECRET", req.diff)

        comment = PrInlineComment(
            filePath="app/auth.py",
            lineNumber=10,
            severity="High",
            comment="Avoid default hardcoded secrets in source control.",
            suggestedPatch="SECRET = os.getenv('JWT_SECRET')"
        )
        resp = PrReviewResponse(
            summary="PR looks good after secret management fix.",
            verdict="APPROVE",
            riskLevel="Low",
            inlineComments=[comment],
            suggestedImprovements=["Add integration test for JWT_SECRET env var."]
        )
        self.assertEqual(resp.verdict, "APPROVE")
        self.assertEqual(len(resp.inlineComments), 1)
        self.assertEqual(resp.inlineComments[0].lineNumber, 10)
        print("PR Review Schemas Validation: PASSED")

    def test_ai_service_health_and_analyze(self):
        """Run async tests against ai-service via ASGI."""
        async def _run():
            async with self.mock_client as client:
                # 1. Health
                res = await client.get("/health")
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.json()["status"], "UP")
                print("1. AI Service Health: OK (UP)")

                # 2. Analyze repository (sample/mock repo)
                analyze_payload = {
                    "repository_url": "example/fastapi-review-engine",
                    "branch": "main"
                }
                res_analyze = await client.post("/analyze", json=analyze_payload)
                self.assertEqual(res_analyze.status_code, 200)
                data = res_analyze.json()
                self.assertIn("maintainability_score", data)
                self.assertIn("findings", data)
                self.assertGreater(len(data["findings"]), 0)
                print(f"2. Analyze succeeded: score={data['maintainability_score']}, debt={data['technical_debt_hours']}h, findings={len(data['findings'])}")

                # 3. Chat with repository (enriched with AST findings & maintainability context)
                chat_payload = {
                    "repository_url": "example/fastapi-review-engine",
                    "branch": "main",
                    "query": "How does authentication work, and what are our main findings?",
                    "maintainability_score": data["maintainability_score"],
                    "technical_debt_hours": data["technical_debt_hours"],
                    "findings": data["findings"][:5],
                }
                res_chat = await client.post("/chat", json=chat_payload)
                self.assertEqual(res_chat.status_code, 200)
                self.assertIn("response", res_chat.json())
                print("3. AST-Enriched Chat response preview:", res_chat.json()["response"][:80])

                # 4. Explain finding with code snippet
                explain_payload = {
                    "repository_url": "example/fastapi-review-engine",
                    "branch": "main",
                    "category": "Security",
                    "severity": "High",
                    "file_path": "app/auth.py",
                    "title": "Token secret should come from environment",
                    "suggestion": "Keep JWT secrets outside source control",
                    "line_number": 42,
                    "code_snippet": "SECRET_KEY = 'hardcoded-secret'\ndef get_secret():\n    return SECRET_KEY"
                }
                res_explain = await client.post("/explain", json=explain_payload)
                self.assertEqual(res_explain.status_code, 200)
                self.assertIn("explanation", res_explain.json())
                self.assertIn("suggestion", res_explain.json())
                print("4. Explain response preview:", res_explain.json()["explanation"][:80])

                # 5. Automated PR Review endpoint (/review/pr)
                pr_payload = {
                    "repository_url": "example/fastapi-review-engine",
                    "branch": "feature/auth-cleanup",
                    "base_branch": "main",
                    "pr_title": "Harden authentication token secret handling",
                    "pr_description": "Load JWT secrets from environment variable instead of hardcoded default.",
                    "diff_or_code": "--- a/app/auth.py\n+++ b/app/auth.py\n@@ -42 +42 @@\n-SECRET_KEY = 'hardcoded-secret'\n+SECRET_KEY = os.getenv('JWT_SECRET', '')",
                    "maintainability_score": data["maintainability_score"],
                    "technical_debt_hours": data["technical_debt_hours"],
                    "findings": data["findings"],
                }
                res_pr = await client.post("/review/pr", json=pr_payload)
                self.assertEqual(res_pr.status_code, 200)
                pr_data = res_pr.json()
                self.assertIn("verdict", pr_data)
                self.assertIn("risk_level", pr_data)
                self.assertIn("summary", pr_data)
                self.assertIn("inline_comments", pr_data)
                self.assertIn("suggested_improvements", pr_data)
                self.assertIsInstance(pr_data["inline_comments"], list)
                print(f"5. Automated PR Review: verdict={pr_data['verdict']}, risk={pr_data['risk_level']}, inline_comments={len(pr_data['inline_comments'])}")

        asyncio.run(_run())

    def test_backend_ai_client_methods(self):
        """Verify backend AiClient forwards AST context and calls AI service successfully."""
        async def _run():
            client = AiClient(base_url="http://testserver")
            transport = httpx.ASGITransport(app=self.ai_app)
            original_async_client = httpx.AsyncClient

            def mock_async_client(*args, **kwargs):
                kwargs["transport"] = transport
                return original_async_client(*args, **kwargs)

            import unittest.mock as mock
            with mock.patch("httpx.AsyncClient", side_effect=mock_async_client):
                # 1. Chat with AST context
                chat_reply = await client.chat(
                    repo_url="example/fastapi-review-engine",
                    query="What are the critical findings?",
                    maintainability_score=82,
                    technical_debt_hours=10,
                    findings=[{"category": "Security", "file": "app/auth.py", "title": "Hardcoded secret", "severity": "High", "suggestion": "Use env var", "line_number": 42}],
                )
                self.assertIsInstance(chat_reply, str)
                self.assertGreater(len(chat_reply), 10)
                print("Backend AiClient.chat with AST Context: PASSED")

                # 2. Explain with code snippet
                explain_res = await client.explain(
                    repo_url="example/fastapi-review-engine",
                    finding={"category": "Security", "severity": "High", "file_path": "app/auth.py", "title": "Secret in code", "suggestion": "Use env", "line_number": 12},
                    code_snippet="API_KEY = 'secret123'",
                )
                self.assertIn("explanation", explain_res)
                self.assertIn("suggestion", explain_res)
                print("Backend AiClient.explain with snippet: PASSED")

                # 3. PR Review
                review_res = await client.review_pr(
                    repo_url="example/fastapi-review-engine",
                    pr_title="PR: Authentication Hardening",
                    diff_or_code="diff --git a/app/auth.py b/app/auth.py",
                    findings=[{"category": "Security", "severity": "High", "file": "app/auth.py", "title": "Hardcoded secret", "suggestion": "Use env", "line_number": 15}],
                    maintainability_score=80,
                    technical_debt_hours=8,
                )
                self.assertIn("verdict", review_res)
                self.assertIn("risk_level", review_res)
                self.assertIn("summary", review_res)
                self.assertIn("inline_comments", review_res)
                print(f"Backend AiClient.review_pr: PASSED (verdict={review_res['verdict']})")

        asyncio.run(_run())

    def test_multi_language_static_scanners(self):
        """Verify multi-language static analysis across JS/TS, Java, Go, and Python."""
        scan_source_file = ai_module.scan_source_file

        # 1. Test TypeScript / React XSS and token storage
        ts_code = """
        import React from 'react';
        export function UserProfile({ bio }: { bio: string }) {
            const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_token_value";
            localStorage.setItem("authToken", token);
            return <div dangerouslySetInnerHTML={{ __html: bio }} />;
        }
        """
        ts_findings, ts_debt = scan_source_file("src/components/UserProfile.tsx", ts_code, ".tsx")
        ts_titles = [f["title"] for f in ts_findings]
        self.assertTrue(any("dangerouslySetInnerHTML" in t for t in ts_titles), f"Missing XSS finding: {ts_titles}")
        self.assertTrue(any("unencrypted browser Web Storage" in t for t in ts_titles), f"Missing storage finding: {ts_titles}")
        self.assertGreaterEqual(ts_debt, 8)
        print("Multi-Language Scanner (TypeScript / React): PASSED")

        # 2. Test Java dynamic SQL and mutable static state
        java_code = """
        package com.example;
        public class UserRepository {
            public static String cacheState = "INITIAL";
            public void findUser(String userId) {
                String query = "SELECT * FROM users WHERE id = " + userId;
                System.out.println("Executing query: " + query);
            }
        }
        """
        java_findings, java_debt = scan_source_file("src/main/java/UserRepository.java", java_code, ".java")
        java_titles = [f["title"] for f in java_findings]
        self.assertTrue(any("dynamic SQL" in t for t in java_titles), f"Missing Java SQL finding: {java_titles}")
        self.assertTrue(any("Non-final mutable static" in t for t in java_titles), f"Missing Java static finding: {java_titles}")
        self.assertTrue(any("Console stdout" in t for t in java_titles), f"Missing Java stdout finding: {java_titles}")
        self.assertGreaterEqual(java_debt, 8)
        print("Multi-Language Scanner (Java): PASSED")

        # 3. Test Go dynamic SQL and panic
        go_code = """
        package handler
        import (
            "database/sql"
            "fmt"
        )
        func QueryUser(db *sql.DB, username string) (*sql.Rows, error) {
            query := fmt.Sprintf("SELECT id, name FROM users WHERE name = '%s'", username)
            return db.Query(query)
        }
        func ValidateState(valid bool) {
            if !valid {
                panic("Invalid application state")
            }
        }
        """
        go_findings, go_debt = scan_source_file("pkg/handler/user.go", go_code, ".go")
        go_titles = [f["title"] for f in go_findings]
        self.assertTrue(any("dynamic SQL" in t for t in go_titles), f"Missing Go SQL finding: {go_titles}")
        self.assertTrue(any("panic()" in t for t in go_titles), f"Missing Go panic finding: {go_titles}")
        self.assertGreaterEqual(go_debt, 8)
        print("Multi-Language Scanner (Go): PASSED")

        # 4. Test Python AST checks
        py_code = """
        import pickle
        def execute_payload(raw_data):
            try:
                obj = pickle.loads(raw_data)
                eval("obj.run()")
            except Exception:
                pass
        """
        py_findings, py_debt = scan_source_file("app/unsafe.py", py_code, ".py")
        py_titles = [f["title"] for f in py_findings]
        self.assertTrue(any("pickle.loads" in t for t in py_titles), f"Missing Python pickle finding: {py_titles}")
        self.assertTrue(any("eval()" in t for t in py_titles), f"Missing Python eval finding: {py_titles}")
        self.assertTrue(any("silently swallowed" in t for t in py_titles), f"Missing Python swallowed exception finding: {py_titles}")
        self.assertGreaterEqual(py_debt, 12)
        print("Multi-Language Scanner (Python AST): PASSED")

    def test_backend_modular_routes(self):
        """Verify backend FastAPI app has all modular APIRouter routes properly mounted."""
        from app.main import app as backend_app
        routes = [r.path for r in backend_app.routes]

        # Auth routes
        self.assertIn("/api/auth/register", routes)
        self.assertIn("/api/auth/login", routes)
        self.assertIn("/api/auth/google", routes)
        self.assertIn("/api/auth/me", routes)
        self.assertIn("/api/auth/github/url", routes)
        self.assertIn("/api/auth/github/callback", routes)
        self.assertIn("/api/auth/github/exchange", routes)

        # Users routes
        self.assertIn("/api/users/profile", routes)
        self.assertIn("/api/users/password", routes)

        # Repositories routes
        self.assertIn("/api/repositories", routes)
        self.assertIn("/api/repositories/github", routes)
        self.assertIn("/api/repositories/github/details", routes)
        self.assertIn("/api/repositories/github/branches", routes)
        self.assertIn("/api/repositories/import", routes)

        # Analysis routes
        self.assertIn("/api/analysis/sample", routes)
        self.assertIn("/api/analysis/latest", routes)
        self.assertIn("/api/analysis/trigger", routes)
        self.assertIn("/api/analysis/{analysis_id}/findings", routes)
        self.assertIn("/api/analysis/history", routes)

        # Reports routes
        self.assertIn("/api/reports/summary", routes)
        self.assertIn("/api/reports/download", routes)

        # AI routes
        self.assertIn("/api/ai/chat", routes)
        self.assertIn("/api/ai/explain", routes)
        self.assertIn("/api/ai/review/pr", routes)

        # Health
        self.assertIn("/api/health", routes)

        print(f"Backend Modular Routes: PASSED (verified {len(routes)} mounted routes)")

    def test_tree_sitter_ast_and_semgrep_engine(self):
        """Verify Tree-Sitter AST Scanner and Semgrep engine integration."""
        ast_scanner_path = ROOT / "ai-service" / "app" / "ast_scanner.py"
        ast_spec = importlib.util.spec_from_file_location("ast_scanner", str(ast_scanner_path))
        ast_mod = importlib.util.module_from_spec(ast_spec)
        ast_spec.loader.exec_module(ast_mod)

        # 1. TreeSitter availability
        self.assertTrue(ast_mod.TreeSitterScanner.is_available(), "TreeSitterScanner should be available")

        # 2. Test JS/TS AST parsing specifically
        js_code = """
        function authenticate(req) {
            eval("req.process()");
            document.getElementById("output").innerHTML = req.body;
        }
        """
        js_ast_findings = ast_mod.TreeSitterScanner.scan_code("src/auth.js", js_code, ".js")
        titles = [f["title"] for f in js_ast_findings]
        self.assertTrue(any("eval()" in t for t in titles), f"Missing eval AST finding: {titles}")
        self.assertTrue(any("innerHTML" in t for t in titles), f"Missing innerHTML AST finding: {titles}")

        # 3. Test Java AST parsing specifically
        java_code = """
        public class PaymentService {
            public static String apiKey = "secret_key_123";
            public void process(java.io.ObjectInputStream in) throws Exception {
                in.readObject();
            }
        }
        """
        java_ast_findings = ast_mod.TreeSitterScanner.scan_code("src/PaymentService.java", java_code, ".java")
        java_titles = [f["title"] for f in java_ast_findings]
        self.assertTrue(any("readObject()" in t for t in java_titles), f"Missing readObject finding: {java_titles}")
        self.assertTrue(any("Non-final mutable static" in t for t in java_titles), f"Missing mutable static finding: {java_titles}")

        # 4. Semgrep Rules catalog check
        semgrep_path = ROOT / "ai-service" / "app" / "semgrep_engine.py"
        sg_spec = importlib.util.spec_from_file_location("semgrep_engine", str(semgrep_path))
        sg_mod = importlib.util.module_from_spec(sg_spec)
        sg_spec.loader.exec_module(sg_mod)

        rules_path = sg_mod.SemgrepEngine.get_rules_path()
        self.assertTrue(rules_path.exists(), f"Semgrep rules file missing: {rules_path}")
        content = rules_path.read_text(encoding="utf-8")
        self.assertIn("javascript-xss-dangerously-set-inner-html", content)
        self.assertIn("java-dynamic-sql-injection", content)
        self.assertIn("go-dynamic-sql-injection", content)
        print("Tree-Sitter AST & Semgrep Engine Integration: PASSED")


if __name__ == "__main__":
    unittest.main()


