import ast
import hashlib
import os
import re
from pathlib import Path
from typing import Any

from app.security_utils import redact_secrets

EXCLUDED_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "venv", ".venv", "env",
    "__pycache__", ".pytest_cache", "dist", "build", ".next", ".nuxt",
    "vendor", "target", "bin", "obj", ".idea", ".vscode"
}

EXCLUDED_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar", ".exe", ".dll",
    ".so", ".dylib", ".class", ".jar", ".war", ".pyc", ".pyo",
    ".min.js", ".min.css", ".map", ".lock", "-lock.json"
}

MAX_FILE_SIZE_BYTES = 500 * 1024  # 500 KB limit per file
TARGET_CHUNK_LINES = 40
CHUNK_OVERLAP_LINES = 6


class CodeChunk:
    def __init__(
        self,
        repository_id: str,
        commit_sha: str,
        file_path: str,
        language: str,
        start_line: int,
        end_line: int,
        content: str,
        symbol: str = "general",
    ):
        self.repository_id = repository_id
        self.commit_sha = commit_sha
        self.file_path = file_path
        self.language = language
        self.start_line = start_line
        self.end_line = end_line
        self.content = redact_secrets(content.strip())
        self.symbol = symbol
        self.content_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "commit_sha": self.commit_sha,
            "file_path": self.file_path,
            "language": self.language,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "symbol": self.symbol,
            "content": self.content,
            "content_hash": self.content_hash,
        }


def detect_file_language(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".php": "php",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".sql": "sql",
        ".sh": "bash",
    }
    return mapping.get(ext, "text")


def chunk_python_code(
    content: str,
    file_path: str,
    repository_id: str,
    commit_sha: str,
) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    lines = content.splitlines(keepends=True)
    if not lines:
        return chunks

    try:
        tree = ast.parse(content)
        extracted_spans: list[tuple[int, int, str]] = []

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = getattr(node, "lineno", 1)
                end = getattr(node, "end_lineno", len(lines))
                name = getattr(node, "name", "symbol")
                extracted_spans.append((start, end, f"{node.__class__.__name__}:{name}"))

        if extracted_spans:
            last_end = 0
            for start, end, symbol in extracted_spans:
                # Capture pre-amble (module imports, global constants, docstrings)
                if start > last_end + 1:
                    gap_text = "".join(lines[last_end:start - 1])
                    if gap_text.strip():
                        chunks.append(CodeChunk(
                            repository_id=repository_id,
                            commit_sha=commit_sha,
                            file_path=file_path,
                            language="python",
                            start_line=last_end + 1,
                            end_line=start - 1,
                            content=gap_text,
                            symbol="module_header",
                        ))
                block_text = "".join(lines[start - 1:end])
                chunks.append(CodeChunk(
                    repository_id=repository_id,
                    commit_sha=commit_sha,
                    file_path=file_path,
                    language="python",
                    start_line=start,
                    end_line=end,
                    content=block_text,
                    symbol=symbol,
                ))
                last_end = end

            # Also capture trailing statements if present
            if last_end < len(lines):
                trailing_text = "".join(lines[last_end:])
                if trailing_text.strip():
                    chunks.append(CodeChunk(
                        repository_id=repository_id,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        language="python",
                        start_line=last_end + 1,
                        end_line=len(lines),
                        content=trailing_text,
                        symbol="module_footer",
                    ))
            return chunks
    except Exception:
        pass  # Fall back to line-based sliding window

    return chunk_by_sliding_window(lines, file_path, "python", repository_id, commit_sha)


def chunk_by_sliding_window(
    lines: list[str],
    file_path: str,
    language: str,
    repository_id: str,
    commit_sha: str,
) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    total_lines = len(lines)
    if total_lines == 0:
        return chunks

    idx = 0
    while idx < total_lines:
        end_idx = min(idx + TARGET_CHUNK_LINES, total_lines)
        chunk_lines = lines[idx:end_idx]
        chunk_text = "".join(chunk_lines)

        # Detect top symbol heuristic
        symbol = "code_block"
        for line in chunk_lines:
            match = re.match(r"^\s*(?:export\s+)?(?:function|class|def|type|interface|func|struct)\s+([a-zA-Z0-9_]+)", line)
            if match:
                symbol = match.group(1)
                break

        chunks.append(CodeChunk(
            repository_id=repository_id,
            commit_sha=commit_sha,
            file_path=file_path,
            language=language,
            start_line=idx + 1,
            end_line=end_idx,
            content=chunk_text,
            symbol=symbol,
        ))

        if end_idx == total_lines:
            break
        idx += TARGET_CHUNK_LINES - CHUNK_OVERLAP_LINES

    return chunks


def chunk_repository_directory(
    root_dir: Path | str,
    repository_id: str,
    commit_sha: str = "HEAD",
    max_files: int = 200,
) -> list[CodeChunk]:
    """
    Scans eligible files in root_dir and produces bounded, metadata-rich CodeChunks.
    """
    root_path = Path(root_dir)
    chunks: list[CodeChunk] = []
    processed_files = 0

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith(".")]

        for filename in filenames:
            if processed_files >= max_files:
                break
            file_ext = os.path.splitext(filename.lower())[1]
            if file_ext in EXCLUDED_EXTS or filename.startswith("."):
                continue

            full_path = Path(dirpath) / filename
            try:
                if full_path.stat().st_size > MAX_FILE_SIZE_BYTES:
                    continue

                rel_path = str(full_path.relative_to(root_path)).replace("\\", "/")
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                if not content.strip():
                    continue

                lang = detect_file_language(rel_path)
                if lang == "python":
                    file_chunks = chunk_python_code(content, rel_path, repository_id, commit_sha)
                else:
                    lines = content.splitlines(keepends=True)
                    file_chunks = chunk_by_sliding_window(lines, rel_path, lang, repository_id, commit_sha)

                chunks.extend(file_chunks)
                processed_files += 1
            except Exception:
                continue

    return chunks
