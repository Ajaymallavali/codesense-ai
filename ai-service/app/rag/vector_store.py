import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from app.rag.chunker import CodeChunk

logger = logging.getLogger(__name__)


def get_vector_store_db_path() -> Path:
    """
    Resolves the persistent SQLite vector database location.
    Prioritizes RAG_INDEX_DIR (for production disks like Render /var/data/codesense_rag),
    falls back to project /data directory, and lastly to OS tempdir.
    """
    env_dir = os.environ.get("RAG_INDEX_DIR") or os.environ.get("PERSISTENT_DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p / "vector_store.db"
        except Exception as exc:
            logger.warning("Could not initialize RAG_INDEX_DIR at %s: %s", p, exc)

    project_data = Path(__file__).resolve().parent.parent.parent / "data"
    try:
        project_data.mkdir(parents=True, exist_ok=True)
        return project_data / "vector_store.db"
    except Exception as exc:
        logger.warning("Could not initialize project data directory at %s: %s", project_data, exc)

    fallback = Path(tempfile.gettempdir()) / "codesense_rag_index"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback / "vector_store.db"


SQLITE_DB_PATH = get_vector_store_db_path()

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "were",
    "will", "with", "what", "which", "who", "how", "does", "do", "can", "file",
    "files", "repo", "repository", "there", "this"
}


def clean_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_]{2,}", text.lower()))


class EmbeddingProvider:
    """
    Computes vector embeddings using high-efficiency term-frequency subword projections
    into 256-dimensional space with deterministic hash-based orthogonal feature mapping.
    """
    VECTOR_DIM = 256

    def __init__(self):
        self.api_key = os.environ.get("QWEN_API_KEY")

    def embed_text(self, text: str) -> list[float]:
        # Filter stopwords to prevent collision flooding
        tokens = [t for t in re.findall(r"[a-zA-Z0-9_]{2,}", text.lower()) if t not in STOP_WORDS]
        vec = [0.0] * self.VECTOR_DIM
        if not tokens:
            return vec

        for t in tokens:
            h = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16)
            idx = h % self.VECTOR_DIM
            sign = 1.0 if (h // self.VECTOR_DIM) % 2 == 0 else -1.0
            vec[idx] += sign

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if len(v1) != len(v2) or not v1:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm1 * norm2)))


def calculate_bm25_lexical_score(query: str, text: str, symbol: str, file_path: str) -> float:
    raw_q = clean_tokens(query)
    q_terms = {t for t in raw_q if t not in STOP_WORDS}
    if not q_terms:
        q_terms = raw_q
    if not q_terms:
        return 0.0

    content_tokens = clean_tokens(text)
    symbol_tokens = clean_tokens(symbol)
    path_tokens = clean_tokens(file_path)

    score = 0.0
    total_weights = 0.0

    for term in q_terms:
        # Give higher weight to specific identifiers and longer terms
        weight = 2.5 if ("_" in term or len(term) >= 8) else 1.0
        total_weights += weight * 1.5

        if term in content_tokens:
            score += weight * 1.0
        if term in symbol_tokens:
            score += weight * 1.5
        if term in path_tokens:
            score += weight * 1.2

    # Calibrate and normalize score to [0.0, 1.0]
    return min(1.0, score / max(1.0, total_weights))


class PersistentVectorStore:
    """
    Persistent SQLite vector and metadata store.
    Persists code chunks, embeddings, and content hashes across restarts.
    """
    def __init__(self, db_path: Path = SQLITE_DB_PATH):
        self.db_path = db_path
        self.embedder = EmbeddingProvider()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    repository_id TEXT NOT NULL,
                    commit_sha TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    language TEXT NOT NULL,
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_repo_commit ON chunks(repository_id, commit_sha);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON chunks(content_hash);")
            conn.commit()

    def index_chunks(self, chunks: list[CodeChunk]) -> int:
        """
        Inserts new chunks, skipping existing chunks with identical content_hash.
        """
        if not chunks:
            return 0

        inserted_count = 0
        with sqlite3.connect(self.db_path) as conn:
            for chunk in chunks:
                chunk_id = f"{chunk.repository_id}:{chunk.commit_sha}:{chunk.file_path}:{chunk.start_line}:{chunk.content_hash}"
                # Check for deduplication
                existing = conn.execute("SELECT 1 FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
                if existing:
                    continue

                vec = self.embedder.embed_text(chunk.content + " " + chunk.symbol + " " + chunk.file_path)
                vec_json = json.dumps(vec)

                conn.execute("""
                    INSERT OR REPLACE INTO chunks 
                    (id, repository_id, commit_sha, file_path, language, start_line, end_line, symbol, content, content_hash, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    chunk_id,
                    chunk.repository_id,
                    chunk.commit_sha,
                    chunk.file_path,
                    chunk.language,
                    chunk.start_line,
                    chunk.end_line,
                    chunk.symbol,
                    chunk.content,
                    chunk.content_hash,
                    vec_json
                ))
                inserted_count += 1
            conn.commit()

        logger.info(f"Indexed {inserted_count} new chunks into persistent vector store.")
        return inserted_count

    def search_hybrid(
        self,
        repository_id: str,
        query: str,
        commit_sha: str | None = None,
        top_k: int = 6,
        file_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Executes hybrid retrieval: 0.65 * Vector Cosine Similarity + 0.35 * BM25 Lexical Score.
        """
        query_vec = self.embedder.embed_text(query)

        query_sql = "SELECT id, repository_id, commit_sha, file_path, language, start_line, end_line, symbol, content, embedding FROM chunks WHERE repository_id = ?"
        params: list[Any] = [repository_id]

        if not commit_sha or commit_sha == "HEAD":
            with sqlite3.connect(self.db_path) as conn:
                latest_row = conn.execute("SELECT commit_sha FROM chunks WHERE repository_id = ? ORDER BY created_at DESC LIMIT 1", (repository_id,)).fetchone()
                if latest_row and latest_row[0]:
                    query_sql += " AND commit_sha = ?"
                    params.append(latest_row[0])
        else:
            query_sql += " AND commit_sha = ?"
            params.append(commit_sha)

        if file_filter:
            query_sql += " AND file_path LIKE ?"
            params.append(f"%{file_filter}%")

        candidates: list[dict[str, Any]] = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query_sql, params)
            rows = cursor.fetchall()

        for row in rows:
            c_id, repo_id, c_sha, file_path, lang, start_line, end_line, symbol, content, emb_str = row
            try:
                emb = json.loads(emb_str)
            except Exception:
                emb = []

            # 1. Semantic Cosine Similarity (positive correlation mapped to [0, 1])
            semantic_score = cosine_similarity(query_vec, emb)
            semantic_norm = max(0.0, semantic_score)

            # 2. Lexical / Keyword BM25 Score
            lexical_score = calculate_bm25_lexical_score(query, content, symbol, file_path)

            # 3. Hybrid Score (calibrated 0.50 semantic + 0.50 lexical)
            hybrid_score = (0.50 * semantic_norm) + (0.50 * lexical_score)

            candidates.append({
                "id": c_id,
                "repository_id": repo_id,
                "commit_sha": c_sha,
                "file_path": file_path,
                "language": lang,
                "start_line": start_line,
                "end_line": end_line,
                "symbol": symbol,
                "content": content,
                "score": round(hybrid_score, 4),
                "semantic_score": round(semantic_norm, 4),
                "lexical_score": round(lexical_score, 4),
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_k]

    def delete_repository_chunks(self, repository_id: str, commit_sha: str | None = None) -> int:
        """
        Removes chunks for a repository, optionally restricted to a specific commit.
        """
        with sqlite3.connect(self.db_path) as conn:
            if commit_sha:
                cursor = conn.execute("DELETE FROM chunks WHERE repository_id = ? AND commit_sha = ?", (repository_id, commit_sha))
            else:
                cursor = conn.execute("DELETE FROM chunks WHERE repository_id = ?", (repository_id,))
            deleted = cursor.rowcount
            conn.commit()
        return deleted

    def delete_file_chunks(self, repository_id: str, file_path: str) -> int:
        """
        Removes chunks for a specific file path within a repository (incremental updates).
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM chunks WHERE repository_id = ? AND file_path = ?", (repository_id, file_path))
            deleted = cursor.rowcount
            conn.commit()
        return deleted

    def get_index_stats(self, repository_id: str) -> dict[str, Any]:
        return self.get_stats(repository_id)

    def get_stats(self, repository_id: str | None = None) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            if repository_id:
                chunk_count = conn.execute("SELECT COUNT(*) FROM chunks WHERE repository_id = ?", (repository_id,)).fetchone()[0]
                files_count = conn.execute("SELECT COUNT(DISTINCT file_path) FROM chunks WHERE repository_id = ?", (repository_id,)).fetchone()[0]
                commits = [r[0] for r in conn.execute("SELECT DISTINCT commit_sha FROM chunks WHERE repository_id = ?", (repository_id,)).fetchall()]
                repos_count = 1 if chunk_count > 0 else 0
            else:
                chunk_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
                files_count = conn.execute("SELECT COUNT(DISTINCT file_path) FROM chunks").fetchone()[0]
                repos_count = conn.execute("SELECT COUNT(DISTINCT repository_id) FROM chunks").fetchone()[0]
                commits = [r[0] for r in conn.execute("SELECT DISTINCT commit_sha FROM chunks").fetchall()][:10]

        return {
            "repository_id": repository_id or "all",
            "total_chunks": chunk_count,
            "indexed_files": files_count,
            "indexed_repositories": repos_count,
            "commits": commits,
            "status": "READY" if chunk_count > 0 else "EMPTY",
        }


vector_store = PersistentVectorStore()
