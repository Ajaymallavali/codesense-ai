import re
from typing import Any

from app.rag.vector_store import vector_store


class Citation:
    def __init__(self, file_path: str, start_line: int, end_line: int, symbol: str = "", finding_id: str | None = None):
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.symbol = symbol
        self.finding_id = finding_id

    def to_dict(self) -> dict[str, Any]:
        data = {
            "filePath": self.file_path,
            "startLine": self.start_line,
            "endLine": self.end_line,
            "symbol": self.symbol,
        }
        if self.finding_id:
            data["findingId"] = self.finding_id
        return data


def sanitize_untrusted_chunk(text: str) -> str:
    """
    Prevents indirect prompt injection by neutralizing instruction escape sequences.
    """
    # Replace attempts to impersonate system messages or prompt directives
    sanitized = re.sub(r"(?i)(?:system prompt|ignore previous instructions|you are now|new instructions:)", "[FILTERED_INSTRUCTION]", text)
    return sanitized


class HybridRetriever:
    """
    Combines hybrid vector + lexical search across repository code chunks with AST findings.
    """
    def __init__(self, store=vector_store):
        self.store = store

    def retrieve(
        self,
        repository_id: str,
        query: str,
        commit_sha: str | None = None,
        findings: list[dict[str, Any]] | None = None,
        top_k: int = 5,
        max_context_chars: int = 8000,
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Returns:
            context_block: Formatted, untrusted-safe XML block for LLM prompt.
            citations: List of structured citations.
        """
        # 1. Retrieve hybrid code chunks
        chunks = self.store.search_hybrid(
            repository_id=repository_id,
            query=query,
            commit_sha=commit_sha,
            top_k=top_k,
        )

        citations: list[dict[str, Any]] = []
        context_parts: list[str] = []
        current_len = 0

        # 2. Match relevant AST findings
        relevant_findings = []
        if findings:
            q_lower = query.lower()
            for f in findings:
                f_title = str(f.get("title", "")).lower()
                f_file = str(f.get("file") or f.get("file_path") or "").lower()
                f_cat = str(f.get("category", "")).lower()
                if any(term in q_lower for term in [f_cat, "issue", "finding", "vulnerab", "smell", "bug", "security"]):
                    relevant_findings.append(f)
                elif any(word in f_title or word in f_file for word in q_lower.split() if len(word) > 3):
                    relevant_findings.append(f)

        if relevant_findings:
            findings_text = ["=== Static AST Findings Relevant to Query ==="]
            for rf in relevant_findings[:6]:
                f_sev = rf.get("severity", "Medium")
                f_file = rf.get("file") or rf.get("file_path") or "unknown"
                f_line = rf.get("line_number") or rf.get("lineNumber") or 1
                f_title = rf.get("title", "")
                f_sug = rf.get("suggestion", "")
                findings_text.append(f"- [{f_sev}] `{f_file}:{f_line}` {f_title} (Fix: {f_sug})")
                citations.append(Citation(
                    file_path=f_file,
                    start_line=f_line,
                    end_line=f_line,
                    symbol="AST_Finding",
                    finding_id=rf.get("id"),
                ).to_dict())
            context_parts.append("\n".join(findings_text))

        # 3. Format source code chunks with strict sandboxing delimiters
        for chunk in chunks:
            chunk_content = sanitize_untrusted_chunk(chunk["content"])
            chunk_xml = (
                f'<source_chunk file="{chunk["file_path"]}" lines="{chunk["start_line"]}-{chunk["end_line"]}" '
                f'symbol="{chunk["symbol"]}" language="{chunk["language"]}">\n'
                f'{chunk_content}\n'
                f'</source_chunk>'
            )

            if current_len + len(chunk_xml) > max_context_chars:
                break

            context_parts.append(chunk_xml)
            current_len += len(chunk_xml)

            citations.append(Citation(
                file_path=chunk["file_path"],
                start_line=chunk["start_line"],
                end_line=chunk["end_line"],
                symbol=chunk["symbol"],
            ).to_dict())

        # Deduplicate citations by (filePath, startLine, endLine)
        unique_citations = []
        seen = set()
        for c in citations:
            key = (c["filePath"], c["startLine"], c["endLine"])
            if key not in seen:
                seen.add(key)
                unique_citations.append(c)

        context_block = "\n\n".join(context_parts) if context_parts else "No direct matching code chunks found."
        return context_block, unique_citations


hybrid_retriever = HybridRetriever()
