import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

RULES_FILE = Path(__file__).resolve().parent / "semgrep_rules.yaml"


class SemgrepEngine:
    """Enterprise Semgrep Runner with fallback to native AST scanner."""

    @staticmethod
    def is_available() -> bool:
        """Check if semgrep binary is installed in system PATH."""
        return shutil.which("semgrep") is not None

    @staticmethod
    def get_rules_path() -> Path:
        return RULES_FILE

    @classmethod
    def scan_directory(cls, target_dir: str) -> list[dict[str, Any]]:
        """Run Semgrep CLI with custom CodeSense rules and map findings."""
        if not cls.is_available():
            logger.info("Semgrep is not installed in PATH; using native Tree-Sitter AST scanner.")
            return []

        rules_path = cls.get_rules_path()
        if not rules_path.exists():
            logger.warning(f"Semgrep rules file not found: {rules_path}")
            return []

        cmd = [
            "semgrep",
            f"--config={str(rules_path)}",
            "--json",
            "--quiet",
            "--no-git-ignore",
            target_dir,
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
            if res.returncode not in (0, 1):
                logger.warning(f"Semgrep exited with return code {res.returncode}: {res.stderr}")
                return []

            data = json.loads(res.stdout or "{}")
            results = data.get("results", [])
            findings: list[dict[str, Any]] = []

            for r in results:
                raw_path = r.get("path", "")
                rel_path = os.path.relpath(raw_path, target_dir).replace("\\", "/")
                start_line = r.get("start", {}).get("line", 1)
                extra = r.get("extra", {})
                meta = extra.get("metadata", {})

                raw_sev = str(extra.get("severity", "WARNING")).upper()
                if raw_sev == "ERROR":
                    severity = "High"
                elif raw_sev == "WARNING":
                    severity = "Medium"
                else:
                    severity = "Low"

                category = meta.get("category", "Security")
                suggestion = meta.get("suggestion", "Remediate code according to secure coding standards.")
                title = extra.get("message") or r.get("check_id") or "Static finding"

                findings.append({
                    "category": category,
                    "file": rel_path,
                    "title": title,
                    "severity": severity,
                    "suggestion": suggestion,
                    "line_number": start_line,
                })

            return findings

        except Exception as exc:
            logger.error(f"Error executing Semgrep CLI: {exc}")
            return []
