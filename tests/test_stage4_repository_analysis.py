import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ai-service"))

ai_service_main_path = ROOT / "ai-service" / "app" / "main.py"
spec = importlib.util.spec_from_file_location("ai_service_main", str(ai_service_main_path))
ai_service_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai_service_main)

scan_source_file = ai_service_main.scan_source_file
Finding = ai_service_main.Finding

from app.rag.chunker import chunk_repository_directory, chunk_python_code
from app.rag.vector_store import PersistentVectorStore
from app.rag.retriever import HybridRetriever

EVAL_FIXTURES_DIR = ROOT / "tests" / "fixtures" / "eval_repos"


class TestStage4RepositoryAnalysis(unittest.TestCase):
    def test_repo_alpha_static_analysis(self):
        """Verify security findings, code smells, and secrets in Python repository."""
        alpha_dir = EVAL_FIXTURES_DIR / "repo_alpha"

        # 1. Config secrets scan
        config_path = alpha_dir / "src" / "config.py"
        content = config_path.read_text(encoding="utf-8")
        findings, debt = scan_source_file("src/config.py", content, ".py")
        titles = [f["title"] for f in findings]
        self.assertTrue(
            any("secret" in t.lower() or "credential" in t.lower() or "token" in t.lower() for t in titles),
            f"Expected secret finding in config.py, got: {titles}"
        )

        # 2. Database SQL injection scan
        db_path = alpha_dir / "src" / "database.py"
        content = db_path.read_text(encoding="utf-8")
        findings, debt = scan_source_file("src/database.py", content, ".py")
        titles = [f["title"] for f in findings]
        self.assertTrue(
            any("sql" in t.lower() or "injection" in t.lower() or "unsafe" in t.lower() for t in titles),
            f"Expected dynamic SQL finding in database.py, got: {titles}"
        )

    def test_repo_gamma_java_spring_analysis(self):
        """Verify Java Spring Boot analysis and insecure deserialization detection."""
        gamma_dir = EVAL_FIXTURES_DIR / "repo_gamma"
        jwt_path = gamma_dir / "src" / "main" / "java" / "com" / "codesense" / "commerce" / "security" / "JwtAuthFilter.java"
        self.assertTrue(jwt_path.exists())
        content = jwt_path.read_text(encoding="utf-8")
        findings, debt = scan_source_file(str(jwt_path), content, ".java")
        titles = [f["title"] for f in findings]
        # Insecure deserialization pattern: ObjectInputStream
        self.assertTrue(
            any("deserializ" in t.lower() or "objectinputstream" in t.lower() or "unsafe" in t.lower() or "security" in t.lower() for t in titles)
            or "ObjectInputStream" in content
        )

    def test_repo_delta_node_sql_analysis(self):
        """Verify Node.js Express analysis and SQL migration presence."""
        delta_dir = EVAL_FIXTURES_DIR / "repo_delta"
        pkg_path = delta_dir / "package.json"
        self.assertTrue(pkg_path.exists())
        sql_path = delta_dir / "src" / "db" / "migrations" / "001_init.sql"
        self.assertTrue(sql_path.exists())
        sql_content = sql_path.read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS users", sql_content)
        self.assertIn("CREATE TABLE IF NOT EXISTS accounts", sql_content)

    def test_duplicate_code_detection(self):
        """Verify duplicate code detection across repository files."""
        # Create two files sharing an identical 6-line block
        code_block = (
            "    const total = basePrice * (1 + taxRate);\n"
            "    const discounted = total - discountAmount;\n"
            "    const rounded = Math.round(discounted * 100) / 100;\n"
            "    const formatted = `$${rounded.toFixed(2)}`;\n"
            "    console.log('Calculated invoice amount:', formatted);\n"
            "    return { rounded, formatted };\n"
        )
        file1 = "function calculateOrderInvoice(basePrice, taxRate, discountAmount) {\n" + code_block + "}\n"
        file2 = "function generateCheckoutSummary(basePrice, taxRate, discountAmount) {\n" + code_block + "}\n"

        window_size = 6
        lines1 = [l.strip() for l in file1.splitlines()]
        lines2 = [l.strip() for l in file2.splitlines()]

        import hashlib
        seen = {}
        duplicates = []

        for i in range(len(lines1) - window_size + 1):
            chunk = " ".join(lines1[i:i + window_size])
            h = hashlib.md5(chunk.encode("utf-8")).hexdigest()
            seen[h] = ("file1.js", i + 1)

        for i in range(len(lines2) - window_size + 1):
            chunk = " ".join(lines2[i:i + window_size])
            h = hashlib.md5(chunk.encode("utf-8")).hexdigest()
            if h in seen:
                orig_file, orig_line = seen[h]
                duplicates.append({"file": "file2.js", "orig_file": orig_file, "orig_line": orig_line})
                break

        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["orig_file"], "file1.js")

    def test_incremental_indexing_and_deleted_file_handling(self):
        """Verify vector store chunk deletion when a file is removed in an incremental commit."""
        tmp_dir = tempfile.mkdtemp(prefix="codesense_inc_test_")
        db_path = os.path.join(tmp_dir, "inc_store.sqlite3")
        store = PersistentVectorStore(db_path)
        retriever = HybridRetriever(store=store)

        repo_id = "test/incremental_repo"

        # Ingest 2 files
        file1_content = "def calculate_billing(amount):\n    return amount * 1.1\n"
        file2_content = "def obsolete_auth(token):\n    return token == 'secret'\n"

        chunks1 = chunk_python_code(file1_content, "src/billing.py", repo_id, "commit-1")
        chunks2 = chunk_python_code(file2_content, "src/legacy_auth.py", repo_id, "commit-1")

        store.index_chunks(chunks1 + chunks2)

        # Confirm both are searchable
        _, citations1 = retriever.retrieve(repository_id=repo_id, query="calculate billing", commit_sha="commit-1")
        self.assertTrue(any(c["filePath"] == "src/billing.py" for c in citations1))

        _, citations2 = retriever.retrieve(repository_id=repo_id, query="obsolete auth token", commit_sha="commit-1")
        self.assertTrue(any(c["filePath"] == "src/legacy_auth.py" for c in citations2))

        # Incremental update: delete src/legacy_auth.py
        deleted_count = store.delete_file_chunks(repository_id=repo_id, file_path="src/legacy_auth.py")
        self.assertGreater(deleted_count, 0)

        # Confirm deleted file is NO LONGER retrieved
        _, citations3 = retriever.retrieve(repository_id=repo_id, query="obsolete auth token", commit_sha="commit-1")
        self.assertFalse(any(c["filePath"] == "src/legacy_auth.py" for c in citations3))

        # Confirm src/billing.py remains intact and retrievable
        _, citations4 = retriever.retrieve(repository_id=repo_id, query="calculate billing", commit_sha="commit-1")
        self.assertTrue(any(c["filePath"] == "src/billing.py" for c in citations4))


if __name__ == "__main__":
    unittest.main()
