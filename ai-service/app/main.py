import os
import shutil
import tempfile
import zipfile
import urllib.request
import json
import ast
import re
from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from app.ast_scanner import TreeSitterScanner
    from app.semgrep_engine import SemgrepEngine
except ImportError:
    try:
        from ast_scanner import TreeSitterScanner
        from semgrep_engine import SemgrepEngine
    except ImportError:
        TreeSitterScanner = None
        SemgrepEngine = None

app = FastAPI(title="CodeSense AI Service", version="0.2.0")


class AnalyzeRepositoryRequest(BaseModel):
    repository_url: str = Field(..., examples=["https://github.com/example/spring-commerce-api"])
    branch: str = "main"
    github_token: str | None = None


class Finding(BaseModel):
    category: str
    file: str
    title: str
    severity: str
    suggestion: str
    line_number: int


class AnalyzeRepositoryResponse(BaseModel):
    repository: str
    branch: str
    maintainability_score: int
    technical_debt_hours: int
    findings: list[Finding]


class ChatRequest(BaseModel):
    repository_url: str
    branch: str = "main"
    github_token: str | None = None
    query: str
    maintainability_score: int | None = None
    technical_debt_hours: int | None = None
    findings: list[dict[str, Any]] | None = None
    code_context: str | None = None


class ExplainRequest(BaseModel):
    repository_url: str
    branch: str = "main"
    github_token: str | None = None
    category: str
    severity: str
    file_path: str
    title: str
    suggestion: str
    line_number: int
    code_snippet: str | None = None


class PrInlineComment(BaseModel):
    file_path: str
    line_number: int | None = None
    severity: str
    comment: str
    suggested_patch: str | None = None


class PrReviewRequest(BaseModel):
    repository_url: str
    branch: str = "main"
    base_branch: str = "main"
    pr_title: str | None = None
    pr_description: str | None = None
    diff_or_code: str | None = None
    findings: list[dict[str, Any]] | None = None
    maintainability_score: int | None = None
    technical_debt_hours: int | None = None
    github_token: str | None = None


class PrReviewResponse(BaseModel):
    summary: str
    verdict: str  # APPROVE, REQUEST_CHANGES, COMMENT
    risk_level: str  # Low, Medium, High, Critical
    inline_comments: list[PrInlineComment]
    suggested_improvements: list[str]


@app.get("/health")
def health() -> dict[str, str]:
    return {"service": "codesense-ai-service", "status": "UP"}


def download_zipball(repo_full_name: str, branch: str, token: str | None, dest_path: str):
    url = f"https://api.github.com/repos/{repo_full_name}/zipball/{branch}"
    current_url = url
    headers = {
        "User-Agent": "CodeSense-AI-Service",
        "Accept": "application/vnd.github+json"
    }
    
    if token and token.strip() and token.strip() != "mock-token":
        headers["Authorization"] = f"Bearer {token.strip()}"

    max_redirects = 5
    redirect_count = 0

    while redirect_count < max_redirects:
        class NoRedirection(urllib.request.HTTPRedirectHandler):
            def http_error_302(self, req, fp, code, msg, headers):
                infourl = urllib.request.addinfourl(fp, headers, req.get_full_url())
                infourl.status = code
                infourl.code = code
                return infourl
            http_error_301 = http_error_303 = http_error_307 = http_error_302

        req = urllib.request.Request(current_url, headers=headers)
        try:
            opener = urllib.request.build_opener(NoRedirection)
            response = opener.open(req)

            if response.status in (301, 302, 303, 307):
                redirect_url = response.headers.get("Location")
                if not redirect_url:
                    raise Exception("Redirect header missing location URL")
                current_url = redirect_url
                if "github.com" not in redirect_url and "api.github.com" not in redirect_url:
                    headers.pop("Authorization", None)
                redirect_count += 1
            else:
                with open(dest_path, "wb") as f:
                    shutil.copyfileobj(response, f)
                return
        except urllib.request.HTTPError as e:
            if e.code == 404 and (not token or token == "mock-token"):
                if "Authorization" in headers:
                    headers.pop("Authorization")
                    current_url = url
                    redirect_count += 1
                    continue
            raise Exception(f"HTTP Error {e.code} downloading zipball")
        except Exception as e:
            raise Exception(f"Failed to fetch zipball: {str(e)}")

    raise Exception("Too many redirects")


def calculate_cognitive_complexity(lines: list[str], ext: str) -> int:
    complexity = 1  # Base complexity
    ext = ext.lower()
    if ext == '.py':
        keywords = ['if ', 'elif ', 'for ', 'while ', 'except ', 'and ', 'or ']
    elif ext in ('.java', '.js', '.jsx', '.ts', '.tsx', '.cs', '.cpp'):
        keywords = ['if ', 'if(', 'for ', 'for(', 'while ', 'while(', 'catch ', 'catch(', '&&', '||', 'case ']
    else:
        keywords = []

    for line in lines:
        cleaned = line.strip()
        if cleaned.startswith('#') or cleaned.startswith('//') or cleaned.startswith('*'):
            continue
        for kw in keywords:
            complexity += cleaned.count(kw)
            
    return complexity


# Python AST Scan Rules
def check_nested_loops(node, depth=0):
    findings = []
    if isinstance(node, (ast.For, ast.While)):
        depth += 1
        if depth > 2:
            findings.append({
                "category": "Complexity",
                "title": "Deeply nested loop detected (depth > 2)",
                "severity": "Medium",
                "suggestion": "Deeply nested loops increase cognitive complexity. Consider refactoring loop logic by extracting inner iterations to helper methods.",
                "line_number": node.lineno
            })
    for child in ast.iter_child_nodes(node):
        findings.extend(check_nested_loops(child, depth))
    return findings


def check_sql_injection(node):
    findings = []
    if isinstance(node, ast.Call):
        func = node.func
        is_execute = False
        if isinstance(func, ast.Attribute) and func.attr == 'execute':
            is_execute = True
        elif isinstance(func, ast.Name) and func.id == 'execute':
            is_execute = True
            
        if is_execute and node.args:
            first_arg = node.args[0]
            is_unsafe = False
            if isinstance(first_arg, ast.BinOp) and isinstance(first_arg.op, ast.Add):
                is_unsafe = True
            elif isinstance(first_arg, ast.JoinedStr):
                is_unsafe = True
            elif isinstance(first_arg, ast.BinOp) and isinstance(first_arg.op, ast.Mod):
                is_unsafe = True
            elif isinstance(first_arg, ast.Call) and isinstance(first_arg.func, ast.Attribute) and first_arg.func.attr == 'format':
                is_unsafe = True
                
            if is_unsafe:
                findings.append({
                    "category": "Security",
                    "title": "Unsafe dynamic SQL statement composition",
                    "severity": "High",
                    "suggestion": "Building SQL queries dynamically using string concatenation or f-strings is vulnerable to SQL injection. Use parameterized queries/prepared statements instead.",
                    "line_number": node.lineno
                })
                
    for child in ast.iter_child_nodes(node):
        findings.extend(check_sql_injection(child))
    return findings


def check_hardcoded_secrets(node):
    findings = []
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id.lower()
                if any(k in name for k in ['key', 'secret', 'password', 'token', 'credential', 'auth_api']):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        val = node.value.value
                        if len(val) > 6 and not any(p in val.lower() for p in ['placeholder', 'test', 'mock', 'replace', 'env']):
                            findings.append({
                                "category": "Security",
                                "title": "Hardcoded credential/secret detected",
                                "severity": "High",
                                "suggestion": "Avoid storing passwords, API keys, or tokens in source code. Retrieve them from secure environment variables or a secrets manager.",
                                "line_number": node.lineno
                            })
    for child in ast.iter_child_nodes(node):
        findings.extend(check_hardcoded_secrets(child))
    return findings


def check_unused_imports(root_node):
    findings = []
    imported_names = {}
    
    for node in ast.walk(root_node):
        if isinstance(node, ast.Import):
            for name in node.names:
                imported_names[name.asname or name.name] = name.lineno
        elif isinstance(node, ast.ImportFrom):
            for name in node.names:
                imported_names[name.asname or name.name] = name.lineno
                
    used_names = set()
    for node in ast.walk(root_node):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used_names.add(node.id)
            
    for name, lineno in imported_names.items():
        if name not in used_names:
            findings.append({
                "category": "Code smell",
                "title": f"Unused import statement ({name})",
                "severity": "Low",
                "suggestion": "Remove unused import statements to keep the codebase clean and reduce unnecessary loading overhead.",
                "line_number": lineno
            })
            
    return findings


def check_magic_numbers(node):
    findings = []
    if isinstance(node, ast.Compare):
        for op in node.comparators:
            if isinstance(op, ast.Constant) and isinstance(op.value, (int, float)):
                val = op.value
                if val not in [0, 1, -1]:
                    findings.append({
                        "category": "Code smell",
                        "title": f"Magic number literal directly used: {val}",
                        "severity": "Low",
                        "suggestion": "Avoid using hardcoded numeric literals in conditions. Assign them to a named constant at the top of the file to improve readability.",
                        "line_number": node.lineno
                    })
    for child in ast.iter_child_nodes(node):
        findings.extend(check_magic_numbers(child))
    return findings


def check_class_and_method_lengths(node):
    findings = []
    if isinstance(node, ast.FunctionDef):
        length = len(node.body)
        if length > 20:
            findings.append({
                "category": "Code smell",
                "title": f"Long method detected ({node.name})",
                "severity": "Medium",
                "suggestion": f"The method '{node.name}' has {length} statements. Consider refactoring it by decomposing it into smaller, cohesive helper functions.",
                "line_number": node.lineno
            })
    elif isinstance(node, ast.ClassDef):
        length = len(node.body)
        if length > 30:
            findings.append({
                "category": "Code smell",
                "title": f"God Class object size warning ({node.name})",
                "severity": "Medium",
                "suggestion": f"The class '{node.name}' has {length} statements. Consider splitting it into smaller classes following the single responsibility principle.",
                "line_number": node.lineno
            })
            
    for child in ast.iter_child_nodes(node):
        findings.extend(check_class_and_method_lengths(child))
    return findings


def check_python_dangerous_calls(root_node):
    findings = []
    for node in ast.walk(root_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in ("eval", "exec"):
                    findings.append({
                        "category": "Security",
                        "title": f"Dangerous dynamic code execution via {node.func.id}()",
                        "severity": "High",
                        "suggestion": f"Avoid using {node.func.id}() as it allows execution of arbitrary code strings.",
                        "line_number": getattr(node, "lineno", 1),
                    })
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr == "loads" and isinstance(node.func.value, ast.Name) and node.func.value.id == "pickle":
                    findings.append({
                        "category": "Security",
                        "title": "Insecure deserialization via pickle.loads()",
                        "severity": "High",
                        "suggestion": "Unpickling untrusted data can lead to arbitrary remote code execution. Use json or protobuf instead.",
                        "line_number": getattr(node, "lineno", 1),
                    })
        elif isinstance(node, ast.ExceptHandler):
            is_broad = node.type is None or (isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException"))
            if is_broad and len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                findings.append({
                    "category": "Code smell",
                    "title": "Broad exception silently swallowed with pass",
                    "severity": "Medium",
                    "suggestion": "Silently swallowing broad exceptions masks underlying bugs and failures. Log the exception or handle specific error types.",
                    "line_number": getattr(node, "lineno", 1),
                })
    return findings


def analyze_python_ast(code_content: str) -> list[dict]:
    try:
        import textwrap
        root = ast.parse(textwrap.dedent(code_content))
        rules = [
            check_nested_loops(root),
            check_sql_injection(root),
            check_hardcoded_secrets(root),
            check_unused_imports(root),
            check_magic_numbers(root),
            check_class_and_method_lengths(root),
            check_python_dangerous_calls(root),
        ]
        all_findings = []
        for r in rules:
            all_findings.extend(r)
        return all_findings
    except Exception:
        # Fall back to empty list if parsing fails
        return []


SECRET_PATTERNS = [
    (re.compile(r'AKIA[0-9A-Z]{16}'), "AWS Access Key ID detected", "High", "Remove AWS access keys from source code and load via IAM roles or environment variables."),
    (re.compile(r'ghp_[0-9a-zA-Z]{36}'), "GitHub Personal Access Token detected", "High", "Remove GitHub access tokens from source files. Retrieve from secrets vault."),
    (re.compile(r'-----BEGIN (?:RSA )?PRIVATE KEY-----'), "Private encryption key embedded in code", "High", "Never commit private cryptographic keys into version control."),
]


def scan_javascript_typescript(rel_path: str, content: str, lines: list[str], ext: str) -> list[dict]:
    findings = []

    # 1. Secret patterns
    for pattern, title, severity, suggestion in SECRET_PATTERNS:
        match = pattern.search(content)
        if match:
            line_no = content[:match.start()].count('\n') + 1
            findings.append({
                "category": "Security",
                "file": rel_path,
                "title": title,
                "severity": severity,
                "suggestion": suggestion,
                "line_number": line_no,
            })

    # 2. Line by line
    for idx, line in enumerate(lines, start=1):
        line_clean = line.strip()
        line_lower = line_clean.lower()
        if line_clean.startswith('//') or line_clean.startswith('*') or line_clean.startswith('/*'):
            continue

        # XSS checks
        if "dangerouslysetinnerhtml" in line_lower:
            findings.append({
                "category": "Security",
                "file": rel_path,
                "title": "Cross-Site Scripting (XSS) risk via dangerouslySetInnerHTML",
                "severity": "High",
                "suggestion": "dangerouslySetInnerHTML injects unescaped HTML into the DOM. Sanitize markup with DOMPurify before rendering.",
                "line_number": idx,
            })
        elif "innerhtml" in line_lower and "=" in line_clean and "sanitiz" not in line_lower:
            findings.append({
                "category": "Security",
                "file": rel_path,
                "title": "Direct DOM innerHTML assignment (XSS risk)",
                "severity": "High",
                "suggestion": "Assigning directly to innerHTML can execute unsanitized scripts. Use textContent or safe DOM nodes.",
                "line_number": idx,
            })
        elif "document.write(" in line_lower:
            findings.append({
                "category": "Security",
                "file": rel_path,
                "title": "Insecure document.write() DOM injection",
                "severity": "High",
                "suggestion": "document.write() bypasses CSP defenses and opens XSS vectors. Use modern DOM manipulation APIs.",
                "line_number": idx,
            })

        # Insecure Execution
        if "eval(" in line_clean:
            findings.append({
                "category": "Security",
                "file": rel_path,
                "title": "Dangerous dynamic code execution via eval()",
                "severity": "High",
                "suggestion": "eval() evaluates arbitrary JavaScript strings. Refactor using structured parsing or JSON.parse().",
                "line_number": idx,
            })
        elif "new Function(" in line_clean:
            findings.append({
                "category": "Security",
                "file": rel_path,
                "title": "Arbitrary code execution via new Function()",
                "severity": "High",
                "suggestion": "Dynamic function constructors evaluate strings as code, posing injection risks.",
                "line_number": idx,
            })

        # Client-side insecure token storage
        if ("localstorage.setitem" in line_lower or "sessionstorage.setitem" in line_lower) and any(k in line_lower for k in ("token", "jwt", "secret", "auth", "credential")):
            findings.append({
                "category": "Security",
                "file": rel_path,
                "title": "Sensitive auth token stored in unencrypted browser Web Storage",
                "severity": "Medium",
                "suggestion": "Web Storage (localStorage/sessionStorage) is accessible to JavaScript and vulnerable to XSS exfiltration. Store tokens in HttpOnly Secure cookies.",
                "line_number": idx,
            })

        # Prototype Pollution
        if "__proto__" in line_clean or "Object.prototype" in line_clean:
            if "=" in line_clean or "assign" in line_clean:
                findings.append({
                    "category": "Security",
                    "file": rel_path,
                    "title": "Potential Prototype Pollution hazard",
                    "severity": "High",
                    "suggestion": "Direct mutation of prototype objects can alter behavior globally. Use Object.create(null) or Map data structures.",
                    "line_number": idx,
                })

        # Hardcoded credentials
        if any(k in line_lower for k in ("apikey", "api_key", "secret", "password", "auth_token")) and ("=" in line_clean or ":" in line_clean):
            if re.search(r'["\'][a-zA-Z0-9_\-]{16,}["\']', line_clean) and not any(p in line_lower for p in ("process.env", "import.meta", "placeholder", "mock", "test", "your-", "dummy")):
                findings.append({
                    "category": "Security",
                    "file": rel_path,
                    "title": "Hardcoded secret or API credential detected",
                    "severity": "High",
                    "suggestion": "Avoid hardcoding secret tokens or API keys. Access them via process.env or secret managers.",
                    "line_number": idx,
                })

        # Unsafe SQL
        if any(kw in line_lower for kw in ("select ", "insert ", "update ", "delete ")) and ("+" in line_clean or "${" in line_clean or ".raw(" in line_lower) and not any(x in line_lower for x in ("console.", "logger", "test", "//")):
            findings.append({
                "category": "Security",
                "file": rel_path,
                "title": "Unsafe dynamic SQL statement composition",
                "severity": "High",
                "suggestion": "Building SQL statements with string concatenation is vulnerable to SQL injection. Utilize parameterized queries.",
                "line_number": idx,
            })

        # Code smells
        if line_clean.startswith("var ") or " var " in line_clean:
            findings.append({
                "category": "Code smell",
                "file": rel_path,
                "title": "Legacy 'var' variable assignment keyword",
                "severity": "Low",
                "suggestion": "Use block-scoped const or let keywords instead of var to minimize hoisting bugs.",
                "line_number": idx,
            })
        if (" == " in line_clean or " != " in line_clean) and "null" not in line_lower and "typeof" not in line_lower:
            findings.append({
                "category": "Code smell",
                "file": rel_path,
                "title": "Loose equality comparison operator used",
                "severity": "Low",
                "suggestion": "Use strict equality operators (=== / !==) to prevent unexpected implicit type coercions.",
                "line_number": idx,
            })
        if "console.log(" in line_clean and not any(x in line_clean for x in ("//", "/*", "*")):
            findings.append({
                "category": "Code smell",
                "file": rel_path,
                "title": "Console logging output statements left in code",
                "severity": "Low",
                "suggestion": "Remove console.log diagnostics or switch to a standard logger before final release.",
                "line_number": idx,
            })

    return findings


def scan_java_source(rel_path: str, content: str, lines: list[str]) -> list[dict]:
    findings = []

    # 1. Global patterns
    for pattern, title, severity, suggestion in SECRET_PATTERNS:
        match = pattern.search(content)
        if match:
            line_no = content[:match.start()].count('\n') + 1
            findings.append({
                "category": "Security",
                "file": rel_path,
                "title": title,
                "severity": severity,
                "suggestion": suggestion,
                "line_number": line_no,
            })

    # Insecure deserialization
    if "objectinputstream" in content.lower() and "readobject" in content.lower():
        findings.append({
            "category": "Security",
            "file": rel_path,
            "title": "Insecure Java deserialization via ObjectInputStream.readObject()",
            "severity": "High",
            "suggestion": "Deserializing untrusted data with readObject() can trigger remote code execution. Enforce ObjectInputFilter or migrate to JSON/protobuf.",
            "line_number": 1,
        })

    # 2. Line by line
    for idx, line in enumerate(lines, start=1):
        line_clean = line.strip()
        line_lower = line_clean.lower()
        if line_clean.startswith("//") or line_clean.startswith("*") or line_clean.startswith("/*"):
            continue

        # Logging stdout
        if "system.out.print" in line_lower or "system.err.print" in line_lower:
            findings.append({
                "category": "Code smell",
                "file": rel_path,
                "title": "Console stdout usage in production",
                "severity": "Low",
                "suggestion": "Avoid System.out.println. Replace with standard Logging API logger instance (e.g. SLF4J / log4j) to manage debug levels.",
                "line_number": idx,
            })
        elif ".printstacktrace(" in line_lower:
            findings.append({
                "category": "Code smell",
                "file": rel_path,
                "title": "Direct printStackTrace() usage",
                "severity": "Low",
                "suggestion": "Avoid calling printStackTrace() directly. Use a structured logger with exception parameters (e.g. log.error('error', e)).",
                "line_number": idx,
            })

        # Static mutable variable
        if "static" in line_clean and "final" not in line_clean and ("public " in line_clean or "private " in line_clean) and ("=" in line_clean) and ("(" not in line_clean and "class " not in line_clean):
            findings.append({
                "category": "Code smell",
                "file": rel_path,
                "title": "Non-final mutable static class variable",
                "severity": "Medium",
                "suggestion": "Static mutable variables introduce concurrency risks. Apply final modifier or encapsulate within getter/setter structures.",
                "line_number": idx,
            })

        # Java dynamic SQL check
        if any(k in line_lower for k in ("select ", "insert ", "update ", "delete ")) and "+" in line_clean and not any(x in line_lower for x in ("log", "//", "system.out")):
            findings.append({
                "category": "Security",
                "file": rel_path,
                "title": "Unsafe dynamic SQL statement composition",
                "severity": "High",
                "suggestion": "Building SQL statements with string concatenation is vulnerable to SQL injection. Utilize parameterized queries / prepared statements.",
                "line_number": idx,
            })

        # Hardcoded secrets
        if any(k in line_lower for k in ("apikey", "api_key", "secret", "password", "token")) and "=" in line_clean and '"' in line_clean:
            if re.search(r'"[a-zA-Z0-9_\-]{8,}"', line_clean) and not any(p in line_lower for p in ("system.getenv", "mock", "test", "dummy", "placeholder")):
                findings.append({
                    "category": "Security",
                    "file": rel_path,
                    "title": "Hardcoded secret or credential in Java source",
                    "severity": "High",
                    "suggestion": "Avoid embedding secrets in Java source code. Use System.getenv() or a Spring @Value configuration property.",
                    "line_number": idx,
                })

    return findings


def scan_go_source(rel_path: str, content: str, lines: list[str]) -> list[dict]:
    findings = []

    # 1. Global patterns
    for pattern, title, severity, suggestion in SECRET_PATTERNS:
        match = pattern.search(content)
        if match:
            line_no = content[:match.start()].count('\n') + 1
            findings.append({
                "category": "Security",
                "file": rel_path,
                "title": title,
                "severity": severity,
                "suggestion": suggestion,
                "line_number": line_no,
            })

    # 2. Line by line
    for idx, line in enumerate(lines, start=1):
        line_clean = line.strip()
        line_lower = line_clean.lower()
        if line_clean.startswith("//") or line_clean.startswith("/*"):
            continue

        # Dynamic SQL injection in Go
        is_sql_call = ("query(" in line_lower or "exec(" in line_lower or "queryrow(" in line_lower) and ("fmt.sprintf" in line_lower or "+" in line_clean)
        is_dynamic_sql = "fmt.sprintf" in line_lower and any(kw in line_lower for kw in ("select ", "insert ", "update ", "delete "))
        if is_sql_call or is_dynamic_sql:
            findings.append({
                "category": "Security",
                "file": rel_path,
                "title": "Unsafe dynamic SQL query construction in Go",
                "severity": "High",
                "suggestion": "Constructing SQL queries using fmt.Sprintf or string concatenation allows SQL injection. Pass arguments directly to db.Query/db.Exec using SQL placeholders ($1, ?).",
                "line_number": idx,
            })

        # Hardcoded credentials
        if any(k in line_lower for k in ("apikey", "api_key", "secret", "password", "token")) and (":=" in line_clean or "=" in line_clean) and '"' in line_clean:
            if re.search(r'"[a-zA-Z0-9_\-]{8,}"', line_clean) and not any(p in line_lower for p in ("os.getenv", "mock", "test", "dummy", "placeholder")):
                findings.append({
                    "category": "Security",
                    "file": rel_path,
                    "title": "Hardcoded credential or API key in Go source",
                    "severity": "High",
                    "suggestion": "Avoid embedding secrets in Go code. Load secrets from environment variables using os.Getenv().",
                    "line_number": idx,
                })

        # Panic in non-test Go code
        if "panic(" in line_clean and not rel_path.endswith("_test.go") and "main.go" not in rel_path:
            findings.append({
                "category": "Code smell",
                "file": rel_path,
                "title": "Direct panic() invocation in library code",
                "severity": "Medium",
                "suggestion": "Avoid calling panic() in Go libraries. Propagate errors gracefully using return (..., error).",
                "line_number": idx,
            })

    return findings


def scan_source_file(rel_path: str, content: str, ext: str) -> tuple[list[dict], int]:
    ext = ext.lower()
    lines = content.splitlines(keepends=True)
    findings = []
    debt_hours = 0

    # 1. Cognitive complexity check
    complexity = calculate_cognitive_complexity(lines, ext)
    if complexity > 15:
        findings.append({
            "category": "Complexity",
            "file": rel_path,
            "title": f"High cognitive complexity metric detected ({complexity})",
            "severity": "Medium",
            "suggestion": f"This file has a calculated cognitive complexity of {complexity} (limit: 15). Consider breaking down long methods, minimizing nested branching, or extracting subroutines.",
            "line_number": 1,
        })
        debt_hours += int(complexity / 4)

    # 2. Long source file check
    if len(lines) > 250:
        findings.append({
            "category": "Code smell",
            "file": rel_path,
            "title": "Long source file (>250 lines)",
            "severity": "Low",
            "suggestion": "Consider refactoring this file by decomposing it into smaller, cohesive modules.",
            "line_number": 1,
        })
        debt_hours += 2

    # 3. Language specific scanners (Tree-Sitter AST & Semantic Heuristics)
    if ext == ".py":
        ast_results = analyze_python_ast(content)
        for af in ast_results:
            findings.append({
                "category": af["category"],
                "file": rel_path,
                "title": af["title"],
                "severity": af["severity"],
                "suggestion": af["suggestion"],
                "line_number": af["line_number"],
            })
    elif ext in (".js", ".jsx", ".ts", ".tsx", ".java", ".go"):
        # First, run high-precision Tree-Sitter AST scanning
        if TreeSitterScanner and TreeSitterScanner.is_available():
            ts_findings = TreeSitterScanner.scan_code(rel_path, content, ext)
            findings.extend(ts_findings)

        # Complement with semantic rule heuristics
        if ext in (".js", ".jsx", ".ts", ".tsx"):
            extra = scan_javascript_typescript(rel_path, content, lines, ext)
        elif ext == ".java":
            extra = scan_java_source(rel_path, content, lines)
        else:
            extra = scan_go_source(rel_path, content, lines)

        # Deduplicate by line number and title
        seen_keys = {(f["line_number"], f["title"]) for f in findings}
        for ef in extra:
            key = (ef["line_number"], ef["title"])
            if key not in seen_keys:
                seen_keys.add(key)
                findings.append(ef)
    else:
        # Check global secrets for any other source files
        for pattern, title, severity, suggestion in SECRET_PATTERNS:
            match = pattern.search(content)
            if match:
                line_no = content[:match.start()].count('\n') + 1
                findings.append({
                    "category": "Security",
                    "file": rel_path,
                    "title": title,
                    "severity": severity,
                    "suggestion": suggestion,
                    "line_number": line_no,
                })

    # Compute technical debt for findings
    for f in findings:
        sev = f.get("severity", "Medium")
        if sev == "High":
            debt_hours += 8
        elif sev == "Medium":
            debt_hours += 4
        else:
            debt_hours += 1

    return findings, debt_hours


def call_gemini(prompt: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise Exception("Gemini API key is not configured")
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json"
    }
    
    body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            data = json.loads(res_body)
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return text
    except Exception as e:
        raise Exception(f"Gemini API request failed: {str(e)}")


@app.post("/analyze", response_model=AnalyzeRepositoryResponse)
def analyze_repository(payload: AnalyzeRepositoryRequest) -> AnalyzeRepositoryResponse:
    repo_name = payload.repository_url
    branch = payload.branch
    token = payload.github_token

    # Check for mock/sample repositories
    is_sample = (
        repo_name.startswith("example/")
        or "spring-commerce-api" in repo_name
        or "django-blog-system" in repo_name
        or "fastapi-review-engine" in repo_name
        or repo_name.startswith("demo/")
    )
    if is_sample:
        if "spring-commerce-api" in repo_name:
            findings = [
                Finding(category="Framework", file="pom.xml", title="Detected Project Architecture: Spring Boot (Java)", severity="Low", suggestion="Keep dependency versions up to date.", line_number=1),
                Finding(category="Complexity", file="src/main/java/com/example/OrderService.java", title="High cognitive complexity metric detected (22)", severity="Medium", suggestion="Consider breaking down long methods, minimizing nested branching.", line_number=24),
                Finding(category="Code smell", file="src/main/java/com/example/PaymentGateway.java", title="Console stdout usage in production", severity="Low", suggestion="Avoid System.out.println. Replace with standard Logging API logger instance.", line_number=89),
                Finding(category="Security", file="src/main/java/com/example/ProductRepository.java", title="Unsafe dynamic SQL statement composition", severity="High", suggestion="Utilize parameterized queries / prepared statements.", line_number=45)
            ]
            maintainability_score = 78
            technical_debt_hours = 12
        elif "django-blog-system" in repo_name:
            findings = [
                Finding(category="Framework", file="requirements.txt", title="Detected Project Architecture: Django / FastAPI / Python", severity="Low", suggestion="Keep dependency versions up to date.", line_number=1),
                Finding(category="Code smell", file="blog/views.py", title="Mutable container as default argument value", severity="High", suggestion="Using mutable containers in default arguments retains object references across calls.", line_number=12),
                Finding(category="Code smell", file="blog/models.py", title="Broad exception catch-all block", severity="Medium", suggestion="Do not swallow broad Exceptions. Specify concrete subtypes.", line_number=54)
            ]
            maintainability_score = 82
            technical_debt_hours = 8
        elif "fastapi-review-engine" in repo_name:
            findings = [
                Finding(category="Framework", file="requirements.txt", title="Detected Project Architecture: FastAPI (Python)", severity="Low", suggestion="Keep dependency versions up to date.", line_number=1),
                Finding(category="Security", file="app/auth.py", title="Token secret should come from environment variables", severity="High", suggestion="Keep JWT secrets outside source control and configure secure environment variables.", line_number=42),
                Finding(category="Complexity", file="app/analyzer.py", title="Cognitive complexity metric elevated (18)", severity="Medium", suggestion="Decompose nested traversal methods into smaller helper functions.", line_number=29),
                Finding(category="Code smell", file="app/models.py", title="Broad exception catch-all block", severity="Medium", suggestion="Catch concrete exception types rather than broad Exception.", line_number=74)
            ]
            maintainability_score = 87
            technical_debt_hours = 11
        else: # react-admin-dashboard
            findings = [
                Finding(category="Framework", file="package.json", title="Detected Project Architecture: React / Node.js", severity="Low", suggestion="Keep dependency versions up to date.", line_number=1),
                Finding(category="Code smell", file="src/components/Sidebar.tsx", title="Loose equality comparison operator used", severity="Low", suggestion="Use strict equality operators (===) to prevent implicit type coercions.", line_number=32),
                Finding(category="Code smell", file="src/utils/auth.ts", title="Console logging output statements left in code", severity="Low", suggestion="Remove console.log diagnostics or switch to a standard logger.", line_number=15)
            ]
            maintainability_score = 94
            technical_debt_hours = 2

        return AnalyzeRepositoryResponse(
            repository=repo_name,
            branch=branch,
            maintainability_score=maintainability_score,
            technical_debt_hours=technical_debt_hours,
            findings=findings
        )

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "repo.zip")
    extract_dir = os.path.join(temp_dir, "extracted")

    findings = []
    technical_debt_hours = 0

    try:
        download_zipball(repo_name, branch, token, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        root_dir = None
        for item in os.listdir(extract_dir):
            item_path = os.path.join(extract_dir, item)
            if os.path.isdir(item_path):
                root_dir = item_path
                break

        if not root_dir:
            root_dir = extract_dir

        code_files = []
        frameworks = []

        ignore_exts = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz', '.class', '.jar', '.war'}

        # Walk workspace and look for projects and settings files
        for dirpath, _, filenames in os.walk(root_dir):
            if any(part.startswith('.') for part in dirpath.split(os.sep)):
                continue
            for file in filenames:
                file_path = os.path.join(dirpath, file)
                _, ext = os.path.splitext(file.lower())
                if ext in ignore_exts:
                    continue
                
                # Register code files
                if ext in {'.java', '.py', '.js', '.jsx', '.ts', '.tsx', '.go', '.rs', '.cpp', '.h', '.cs', '.php', '.rb'}:
                    code_files.append((file_path, ext))

                # Identify build frameworks
                if file == "pom.xml" or file == "build.gradle":
                    frameworks.append("Spring Boot (Java)")
                elif file == "package.json":
                    frameworks.append("React / Node.js")
                elif file == "requirements.txt" or file == "pyproject.toml":
                    frameworks.append("FastAPI / Python")
                elif file == "go.mod":
                    frameworks.append("Go Module")
                elif file == "Cargo.toml":
                    frameworks.append("Rust Cargo")

        frameworks = list(set(frameworks))
        if frameworks:
            findings.append(Finding(
                category="Framework",
                file="Project Configuration",
                title=f"Detected Project Architecture: {', '.join(frameworks)}",
                severity="Low",
                suggestion="This architecture dictates dependency layout and code conventions. Keep dependency versions up to date.",
                line_number=1
            ))

        # Perform metrics and rules scanning
        for fpath, ext in code_files:
            rel_path = os.path.relpath(fpath, root_dir).replace("\\", "/")
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                file_findings, debt = scan_source_file(rel_path, content, ext)
                for ff in file_findings:
                    findings.append(Finding(
                        category=ff["category"],
                        file=ff.get("file", rel_path),
                        title=ff["title"],
                        severity=ff["severity"],
                        suggestion=ff["suggestion"],
                        line_number=ff.get("line_number", 1)
                    ))
                technical_debt_hours += debt
            except Exception:
                pass

        # Optional Semgrep Integration (if installed on host)
        if SemgrepEngine and SemgrepEngine.is_available():
            semgrep_results = SemgrepEngine.scan_directory(root_dir)
            seen_semgrep = {(f.line_number, f.title) for f in findings}
            for sf in semgrep_results:
                if (sf["line_number"], sf["title"]) not in seen_semgrep:
                    seen_semgrep.add((sf["line_number"], sf["title"]))
                    findings.append(Finding(
                        category=sf["category"],
                        file=sf["file"],
                        title=sf["title"],
                        severity=sf["severity"],
                        suggestion=sf["suggestion"],
                        line_number=sf["line_number"]
                    ))
                    if sf["severity"] == "High":
                        technical_debt_hours += 8
                    elif sf["severity"] == "Medium":
                        technical_debt_hours += 4
                    else:
                        technical_debt_hours += 1

        # Calculate dynamic Maintainability Score
        high_issues = sum(1 for f in findings if f.severity == "High")
        med_issues = sum(1 for f in findings if f.severity == "Medium")
        low_issues = sum(1 for f in findings if f.severity == "Low")

        maintainability_score = max(30, 98 - (high_issues * 8) - (med_issues * 4) - (low_issues * 1.5))
        maintainability_score = int(min(100, maintainability_score))

        if not findings:
            sample_file = os.path.relpath(code_files[0][0], root_dir) if code_files else "README.md"
            findings.append(Finding(
                category="Documentation",
                file=sample_file,
                title="Missing inline API descriptors",
                severity="Low",
                suggestion="Add standard documentation comments to describe public module actions and input structures.",
                line_number=1
            ))
            maintainability_score = 92
            technical_debt_hours = 2

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Analysis engine failed: {str(e)}")

    shutil.rmtree(temp_dir, ignore_errors=True)

    return AnalyzeRepositoryResponse(
        repository=repo_name,
        branch=branch,
        maintainability_score=maintainability_score,
        technical_debt_hours=technical_debt_hours,
        findings=findings
    )


@app.post("/chat")
def chat(payload: ChatRequest):
    try:
        # Construct AST findings and repository context block
        context_parts = []
        if payload.maintainability_score is not None:
            context_parts.append(f"Repository Maintainability Score: {payload.maintainability_score}/100")
        if payload.technical_debt_hours is not None:
            context_parts.append(f"Estimated Technical Debt: {payload.technical_debt_hours} hours")
        if payload.findings:
            findings_summary = []
            for f in payload.findings[:15]:
                f_sev = f.get("severity", "Medium")
                f_cat = f.get("category", "Smell")
                f_file = f.get("file") or f.get("file_path") or "unknown"
                f_line = f.get("line_number") or f.get("lineNumber") or 1
                f_title = f.get("title", "")
                f_sug = f.get("suggestion", "")
                findings_summary.append(f"- [{f_sev}] ({f_cat}) {f_file}:{f_line} - {f_title} (Fix: {f_sug})")
            context_parts.append("Key AST & Static Analysis Findings:\n" + "\n".join(findings_summary))
        if payload.code_context:
            context_parts.append(f"Source Code Context:\n{payload.code_context[:2500]}")

        context_block = "\n\n".join(context_parts) if context_parts else "No recorded static findings."

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if api_key:
            prompt = (
                f"You are CodeSense AI senior software architect and code review expert.\n"
                f"Repository: '{payload.repository_url}' (Branch: '{payload.branch}')\n\n"
                f"=== Repository Context & AST Findings ===\n"
                f"{context_block}\n\n"
                f"=== Developer Query ===\n"
                f"{payload.query}\n\n"
                f"Provide a thorough, developer-oriented answer citing specific files, lines, and AST smells from the findings when appropriate."
            )
            response_text = call_gemini(prompt)
            return {"response": response_text}

        # Context-aware intelligent fallback if Gemini API key is not configured
        q = payload.query.lower()
        if payload.findings and any(k in q for k in ["finding", "issue", "problem", "vulnerability", "smell", "security", "bug", "list"]):
            top_f = payload.findings[:6]
            lines = [f"Top AST issues detected in '{payload.repository_url}':"]
            for f in top_f:
                lines.append(f"• [{f.get('severity', 'Med')}] {f.get('file') or f.get('file_path')}:{f.get('line_number', 1)} - {f.get('title')}")
                if f.get("suggestion"):
                    lines.append(f"  Fix: {f.get('suggestion')}")
            if payload.maintainability_score is not None:
                lines.append(f"\nOverall score: {payload.maintainability_score}/100 with ~{payload.technical_debt_hours or 0}h debt.")
            return {"response": "\n".join(lines)}

        if "sql" in q or "injection" in q:
            response_text = "Regarding SQL Injection: Build all SQL statement executions using Prepared Statements or parameterized inputs rather than direct string concatenation."
        elif "loop" in q or "complexity" in q:
            response_text = "Regarding loop nested depth: Deeply nested iterations increase cognitive complexity. Decompose nested loops into single-tier helper methods."
        elif "secret" in q or "password" in q or "token" in q:
            response_text = "Regarding secrets: Storing clear-text strings like API key definitions inside source code exposes credentials. Use environment variables (.env) read securely at runtime."
        else:
            response_text = (
                f"I reviewed repository '{payload.repository_url}' on branch '{payload.branch}'. "
                f"Maintainability score is {payload.maintainability_score or 88}/100 with {len(payload.findings or [])} detected AST findings. "
                f"You can ask me to explain any finding, suggest code patches, or run an automated PR review."
            )
        return {"response": response_text}

    except Exception as e:
        return {"response": f"AI Chat could not complete: {str(e)}"}


@app.post("/explain")
def explain(payload: ExplainRequest):
    try:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        snippet_text = f"\nSource Snippet:\n```\n{payload.code_snippet}\n```" if payload.code_snippet else ""

        if api_key:
            prompt = (
                f"You are CodeSense AI senior code reviewer.\n"
                f"Provide a clear technical explanation and a corrected code block for the following finding in repository '{payload.repository_url}' (Branch: '{payload.branch}'):\n"
                f"- File: {payload.file_path} at line {payload.line_number}\n"
                f"- Category: {payload.category}\n"
                f"- Severity: {payload.severity}\n"
                f"- Issue Title: {payload.title}\n"
                f"- Suggestion: {payload.suggestion}\n"
                f"{snippet_text}\n\n"
                f"Format your response with a concise 'Explanation' section and a 'Suggested Fix' code block."
            )
            response_text = call_gemini(prompt)

            parts = response_text.split("```")
            suggested_code = "No suggested code block generated."
            for part in parts:
                if part.strip().startswith(("python", "java", "javascript", "typescript", "cpp", "go", "json", "sql")):
                    suggested_code = "```" + part + "```"
                    break

            return {
                "explanation": response_text,
                "suggestion": suggested_code
            }

        # Intelligent heuristic fallback with code patch
        explanation = (
            f"The issue '{payload.title}' was flagged in '{payload.file_path}' at line {payload.line_number} "
            f"under the '{payload.category}' category with '{payload.severity}' severity.\n\n"
            f"Why this matters: This violates standard code maintainability and security conventions.\n\n"
            f"Recommendation: {payload.suggestion}"
        )

        title_lower = payload.title.lower()
        if "sql" in title_lower or "injection" in title_lower:
            suggested_code = (
                "```python\n"
                "# Use parameterized query instead of string formatting:\n"
                "cursor.execute(\"SELECT * FROM items WHERE id = %s\", (item_id,))\n"
                "```"
            )
        elif "secret" in title_lower or "token" in title_lower or "password" in title_lower:
            suggested_code = (
                "```python\n"
                "import os\n"
                "# Load credentials securely from environment variables:\n"
                "API_KEY = os.environ.get('SERVICE_API_KEY')\n"
                "```"
            )
        elif "loop" in title_lower or "complexity" in title_lower:
            suggested_code = (
                "```python\n"
                "# Extract inner iteration to dedicated helper function:\n"
                "def process_batch(items):\n"
                "    return [transform(item) for item in items if is_valid(item)]\n"
                "```"
            )
        else:
            suggested_code = (
                f"```python\n"
                f"# Suggested refactoring for {payload.file_path}:{payload.line_number}\n"
                f"# {payload.suggestion}\n"
                f"```"
            )

        return {
            "explanation": explanation,
            "suggestion": suggested_code
        }

    except Exception as e:
        return {
            "explanation": f"AI Explanation failed: {str(e)}",
            "suggestion": "No suggested code block generated due to error."
        }


@app.post("/review/pr", response_model=PrReviewResponse)
def review_pr(payload: PrReviewRequest) -> PrReviewResponse:
    try:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        findings = payload.findings or []

        high_count = sum(1 for f in findings if str(f.get("severity", "")).lower() == "high")
        med_count = sum(1 for f in findings if str(f.get("severity", "")).lower() == "medium")

        if high_count > 0:
            default_verdict = "REQUEST_CHANGES"
            default_risk = "High" if high_count < 3 else "Critical"
        elif med_count > 0:
            default_verdict = "COMMENT"
            default_risk = "Medium"
        else:
            default_verdict = "APPROVE"
            default_risk = "Low"

        if api_key:
            prompt = (
                f"You are CodeSense AI senior software architect conducting an automated Pull Request review.\n"
                f"Repository: '{payload.repository_url}' (Branch: '{payload.branch}')\n"
                f"PR Title: {payload.pr_title or 'Automated Quality & Security PR Review'}\n"
                f"PR Description: {payload.pr_description or 'Review of current branch changes and static AST findings.'}\n"
                f"Maintainability Score: {payload.maintainability_score or 'N/A'}/100\n"
                f"Detected AST Findings:\n" + json.dumps(findings[:15], indent=2) + "\n\n"
                f"Provide a structured JSON response with keys:\n"
                f"- 'summary': (detailed string summary of PR quality)\n"
                f"- 'verdict': (one of 'APPROVE', 'REQUEST_CHANGES', 'COMMENT')\n"
                f"- 'risk_level': (one of 'Low', 'Medium', 'High', 'Critical')\n"
                f"- 'inline_comments': list of objects with 'file_path', 'line_number', 'severity', 'comment', 'suggested_patch'\n"
                f"- 'suggested_improvements': list of actionable string suggestions\n"
                f"Return ONLY valid JSON."
            )
            try:
                res_text = call_gemini(prompt)
                clean_json = res_text.strip()
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                parsed = json.loads(clean_json)
                return PrReviewResponse(
                    summary=parsed.get("summary", "PR review completed."),
                    verdict=parsed.get("verdict", default_verdict),
                    risk_level=parsed.get("risk_level", default_risk),
                    inline_comments=[PrInlineComment(**c) for c in parsed.get("inline_comments", [])],
                    suggested_improvements=parsed.get("suggested_improvements", [])
                )
            except Exception as parse_err:
                pass

        # Intelligent Fallback PR Review Synthesis
        inline_comments = []
        improvements = []

        for f in findings:
            file_name = f.get("file") or f.get("file_path") or "unknown"
            line_no = f.get("line_number") or f.get("lineNumber") or 1
            sev = f.get("severity", "Medium")
            title = f.get("title", "Code smell detected")
            sug = f.get("suggestion", "")

            patch = None
            t_low = title.lower()
            if "sql" in t_low or "injection" in t_low:
                patch = "cursor.execute(\"SELECT * FROM items WHERE id = %s\", (item_id,))"
            elif "secret" in t_low or "token" in t_low:
                patch = "API_KEY = os.environ.get('API_SECRET_KEY')"
            elif "loop" in t_low or "complexity" in t_low:
                patch = "def process_inner(batch):\n    return [item.compute() for item in batch]"

            inline_comments.append(PrInlineComment(
                file_path=file_name,
                line_number=line_no,
                severity=sev,
                comment=f"{title}. {sug}",
                suggested_patch=patch
            ))
            improvements.append(f"Refactor {file_name}:{line_no} to resolve {title.lower()}")

        if not improvements:
            improvements = [
                "Maintain test coverage across newly added endpoints",
                "Ensure environment configurations follow 12-factor principles"
            ]

        summary = (
            f"Automated CodeSense PR review for branch '{payload.branch}'. "
            f"Evaluated {len(findings)} AST static issues ({high_count} High, {med_count} Medium). "
            f"Maintainability score estimated at {payload.maintainability_score or 88}/100."
        )

        return PrReviewResponse(
            summary=summary,
            verdict=default_verdict,
            risk_level=default_risk,
            inline_comments=inline_comments,
            suggested_improvements=improvements[:5]
        )
    except Exception as exc:
        return PrReviewResponse(
            summary=f"Automated PR review encountered an issue: {str(exc)}",
            verdict="COMMENT",
            risk_level="Medium",
            inline_comments=[],
            suggested_improvements=["Run static analysis manually to inspect potential smells."]
        )
