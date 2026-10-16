import re
import warnings
from typing import Any

warnings.filterwarnings("ignore", category=FutureWarning)

try:
    import tree_sitter_languages
    HAS_TREE_SITTER = True
    _PARSERS: dict[str, Any] = {
        "js": tree_sitter_languages.get_parser("javascript"),
        "ts": tree_sitter_languages.get_parser("typescript"),
        "tsx": tree_sitter_languages.get_parser("tsx"),
        "java": tree_sitter_languages.get_parser("java"),
        "go": tree_sitter_languages.get_parser("go"),
    }
except Exception:
    HAS_TREE_SITTER = False
    _PARSERS = {}

SECRET_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID detected", "High", "Remove AWS access keys from source code and load via IAM roles or environment variables."),
    (re.compile(r"ghp_[0-9a-zA-Z]{36}"), "GitHub Personal Access Token detected", "High", "Remove GitHub access tokens from source files. Retrieve from secrets vault."),
    (re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----"), "Private encryption key embedded in code", "High", "Never commit private cryptographic keys into version control."),
]


def _scan_js_ts_ast(root_node: Any, rel_path: str, code_bytes: bytes) -> list[dict]:
    findings: list[dict] = []

    def visitor(node: Any) -> None:
        ntype = node.type
        line_no = node.start_point[0] + 1
        node_text = node.text.decode("utf-8", errors="ignore")

        # 1. JSX XSS (dangerouslySetInnerHTML)
        if ntype in ("jsx_attribute", "jsx_self_closing_element", "jsx_element"):
            if "dangerouslySetInnerHTML" in node_text:
                findings.append({
                    "category": "Security",
                    "file": rel_path,
                    "title": "Cross-Site Scripting (XSS) risk via dangerouslySetInnerHTML",
                    "severity": "High",
                    "suggestion": "dangerouslySetInnerHTML injects unescaped HTML into the DOM. Sanitize markup with DOMPurify before rendering.",
                    "line_number": line_no,
                })

        # 2. Call Expressions (eval, new Function, localStorage, document.write, setTimeout)
        if ntype == "call_expression":
            fn_node = node.child_by_field_name("function")
            fn_text = fn_node.text.decode("utf-8", errors="ignore") if fn_node else ""

            if fn_text == "eval":
                findings.append({
                    "category": "Security",
                    "file": rel_path,
                    "title": "Dangerous dynamic code execution via eval()",
                    "severity": "High",
                    "suggestion": "eval() evaluates arbitrary JavaScript strings. Refactor using structured parsing or JSON.parse().",
                    "line_number": line_no,
                })
            elif fn_text == "Function" or "new Function" in node_text:
                findings.append({
                    "category": "Security",
                    "file": rel_path,
                    "title": "Arbitrary code execution via new Function()",
                    "severity": "High",
                    "suggestion": "Dynamic function constructors evaluate strings as code, posing injection risks.",
                    "line_number": line_no,
                })
            elif "localStorage.setItem" in fn_text or "sessionStorage.setItem" in fn_text:
                args_node = node.child_by_field_name("arguments")
                args_text = args_node.text.decode("utf-8", errors="ignore").lower() if args_node else ""
                if any(k in args_text for k in ("token", "jwt", "secret", "auth", "credential")):
                    findings.append({
                        "category": "Security",
                        "file": rel_path,
                        "title": "Sensitive auth token stored in unencrypted browser Web Storage",
                        "severity": "Medium",
                        "suggestion": "Web Storage (localStorage/sessionStorage) is accessible to JavaScript and vulnerable to XSS exfiltration. Store tokens in HttpOnly Secure cookies.",
                        "line_number": line_no,
                    })
            elif fn_text in ("document.write", "document.writeln"):
                findings.append({
                    "category": "Security",
                    "file": rel_path,
                    "title": "Insecure document.write() DOM injection",
                    "severity": "High",
                    "suggestion": "document.write() bypasses CSP defenses and opens XSS vectors. Use modern DOM manipulation APIs.",
                    "line_number": line_no,
                })
            elif fn_text == "console.log":
                findings.append({
                    "category": "Code smell",
                    "file": rel_path,
                    "title": "Console logging output statements left in code",
                    "severity": "Low",
                    "suggestion": "Remove console.log diagnostics or switch to a standard logger before final release.",
                    "line_number": line_no,
                })

        # 3. Direct DOM innerHTML / outerHTML assignment & Prototype Pollution
        if ntype == "assignment_expression":
            left_node = node.child_by_field_name("left")
            left_text = left_node.text.decode("utf-8", errors="ignore") if left_node else ""

            if left_text.endswith(".innerHTML") or left_text.endswith(".outerHTML"):
                if "sanitiz" not in node_text.lower():
                    findings.append({
                        "category": "Security",
                        "file": rel_path,
                        "title": "Direct DOM innerHTML assignment (XSS risk)",
                        "severity": "High",
                        "suggestion": "Assigning directly to innerHTML can execute unsanitized scripts. Use textContent or safe DOM nodes.",
                        "line_number": line_no,
                    })
            elif "__proto__" in left_text or "Object.prototype" in left_text:
                findings.append({
                    "category": "Security",
                    "file": rel_path,
                    "title": "Potential Prototype Pollution hazard",
                    "severity": "High",
                    "suggestion": "Direct mutation of prototype objects can alter behavior globally. Use Object.create(null) or Map data structures.",
                    "line_number": line_no,
                })

        # 4. Binary Expressions (Unsafe dynamic SQL concatenation, loose equality)
        if ntype == "binary_expression":
            left_node = node.child_by_field_name("left")
            right_node = node.child_by_field_name("right")
            left_text = left_node.text.decode("utf-8", errors="ignore").lower() if left_node else ""
            right_text = right_node.text.decode("utf-8", errors="ignore").lower() if right_node else ""

            # Check dynamic SQL string concatenation
            sql_keywords = ("select ", "insert ", "update ", "delete ", "from ", "where ")
            if any(k in left_text or k in right_text for k in sql_keywords) and "+" in node_text:
                if not any(x in node_text.lower() for x in ("console.", "logger", "test", "//")):
                    findings.append({
                        "category": "Security",
                        "file": rel_path,
                        "title": "Unsafe dynamic SQL statement composition",
                        "severity": "High",
                        "suggestion": "Building SQL statements with string concatenation is vulnerable to SQL injection. Utilize parameterized queries.",
                        "line_number": line_no,
                    })

            # Check loose equality
            op_node = node.child_by_field_name("operator")
            op_text = op_node.text.decode("utf-8", errors="ignore") if op_node else ""
            if op_text in ("==", "!=") and "null" not in node_text.lower() and "typeof" not in node_text.lower():
                findings.append({
                    "category": "Code smell",
                    "file": rel_path,
                    "title": "Loose equality comparison operator used",
                    "severity": "Low",
                    "suggestion": "Use strict equality operators (=== / !==) to prevent unexpected implicit type coercions.",
                    "line_number": line_no,
                })

        # 5. Template literals with SQL and interpolation
        if ntype == "template_string":
            if any(k in node_text.lower() for k in ("select ", "insert ", "update ", "delete ")) and "${" in node_text:
                if not any(x in node_text.lower() for x in ("console.", "logger", "test")):
                    findings.append({
                        "category": "Security",
                        "file": rel_path,
                        "title": "Unsafe dynamic SQL statement composition in template literal",
                        "severity": "High",
                        "suggestion": "Building SQL statements with string interpolation is vulnerable to SQL injection. Utilize parameterized queries.",
                        "line_number": line_no,
                    })

        # 6. Legacy 'var' declarations
        if ntype == "variable_declaration":
            first_child = node.children[0] if node.children else None
            if first_child and first_child.text.decode("utf-8", errors="ignore") == "var":
                findings.append({
                    "category": "Code smell",
                    "file": rel_path,
                    "title": "Legacy 'var' variable assignment keyword",
                    "severity": "Low",
                    "suggestion": "Use block-scoped const or let keywords instead of var to minimize hoisting bugs.",
                    "line_number": line_no,
                })

        for child in node.children:
            visitor(child)

    visitor(root_node)
    return findings


def _scan_java_ast(root_node: Any, rel_path: str, code_bytes: bytes) -> list[dict]:
    findings: list[dict] = []

    def visitor(node: Any) -> None:
        ntype = node.type
        line_no = node.start_point[0] + 1
        node_text = node.text.decode("utf-8", errors="ignore")

        # 1. Non-final mutable static class variable
        if ntype == "field_declaration":
            mods = [c.text.decode("utf-8", errors="ignore") for c in node.children if c.type in ("modifiers", "modifier")]
            mods_str = " ".join(mods)
            if "static" in mods_str and "final" not in mods_str:
                findings.append({
                    "category": "Code smell",
                    "file": rel_path,
                    "title": "Non-final mutable static class variable",
                    "severity": "Medium",
                    "suggestion": "Static mutable variables introduce concurrency risks. Apply final modifier or encapsulate within getter/setter structures.",
                    "line_number": line_no,
                })

        # 2. Method Invocations (readObject, println, printStackTrace)
        if ntype == "method_invocation":
            name_node = node.child_by_field_name("name")
            name_text = name_node.text.decode("utf-8", errors="ignore") if name_node else ""

            if name_text == "readObject":
                findings.append({
                    "category": "Security",
                    "file": rel_path,
                    "title": "Insecure Java deserialization via ObjectInputStream.readObject()",
                    "severity": "High",
                    "suggestion": "Deserializing untrusted data with readObject() can trigger remote code execution. Enforce ObjectInputFilter or migrate to JSON/protobuf.",
                    "line_number": line_no,
                })
            elif name_text in ("println", "print") and ("System.out" in node_text or "System.err" in node_text):
                findings.append({
                    "category": "Code smell",
                    "file": rel_path,
                    "title": "Console stdout usage in production",
                    "severity": "Low",
                    "suggestion": "Avoid System.out.println. Replace with standard Logging API logger instance (e.g. SLF4J / log4j) to manage debug levels.",
                    "line_number": line_no,
                })
            elif name_text == "printStackTrace":
                findings.append({
                    "category": "Code smell",
                    "file": rel_path,
                    "title": "Direct printStackTrace() usage",
                    "severity": "Low",
                    "suggestion": "Avoid calling printStackTrace() directly. Use a structured logger with exception parameters (e.g. log.error('error', e)).",
                    "line_number": line_no,
                })

        # 3. Dynamic SQL concatenation in Java
        if ntype == "binary_expression":
            left_node = node.child_by_field_name("left")
            right_node = node.child_by_field_name("right")
            left_text = left_node.text.decode("utf-8", errors="ignore").lower() if left_node else ""
            right_text = right_node.text.decode("utf-8", errors="ignore").lower() if right_node else ""

            sql_keywords = ("select ", "insert ", "update ", "delete ")
            if any(k in left_text or k in right_text for k in sql_keywords) and "+" in node_text:
                if not any(x in node_text.lower() for x in ("log", "//", "system.out")):
                    findings.append({
                        "category": "Security",
                        "file": rel_path,
                        "title": "Unsafe dynamic SQL statement composition",
                        "severity": "High",
                        "suggestion": "Building SQL statements with string concatenation is vulnerable to SQL injection. Utilize parameterized queries / prepared statements.",
                        "line_number": line_no,
                    })

        # 4. Empty catch block
        if ntype == "catch_clause":
            body_node = node.child_by_field_name("body")
            if body_node:
                named_children = [c for c in body_node.children if c.is_named]
                if len(named_children) == 0:
                    findings.append({
                        "category": "Code smell",
                        "file": rel_path,
                        "title": "Empty catch block silently swallowing exceptions",
                        "severity": "Medium",
                        "suggestion": "Empty catch block silently swallows exceptions, hiding runtime failures. Log the exception or rethrow.",
                        "line_number": line_no,
                    })

        for child in node.children:
            visitor(child)

    visitor(root_node)
    return findings


def _scan_go_ast(root_node: Any, rel_path: str, code_bytes: bytes) -> list[dict]:
    findings: list[dict] = []

    def visitor(node: Any) -> None:
        ntype = node.type
        line_no = node.start_point[0] + 1
        node_text = node.text.decode("utf-8", errors="ignore")

        if ntype == "call_expression":
            fn_node = node.child_by_field_name("function")
            fn_text = fn_node.text.decode("utf-8", errors="ignore") if fn_node else ""

            # Panic in library code
            if fn_text == "panic" and not rel_path.endswith("_test.go") and "main.go" not in rel_path:
                findings.append({
                    "category": "Code smell",
                    "file": rel_path,
                    "title": "Direct panic() invocation in library code",
                    "severity": "Medium",
                    "suggestion": "Avoid calling panic() in Go libraries. Propagate errors gracefully using return (..., error).",
                    "line_number": line_no,
                })

            # Dynamic SQL queries in Go
            is_db_query = any(k in fn_text for k in ("Query", "Exec", "QueryRow"))
            args_node = node.child_by_field_name("arguments")
            args_text = args_node.text.decode("utf-8", errors="ignore") if args_node else ""

            if is_db_query and ("fmt.Sprintf" in args_text or "+" in args_text):
                findings.append({
                    "category": "Security",
                    "file": rel_path,
                    "title": "Unsafe dynamic SQL query construction in Go",
                    "severity": "High",
                    "suggestion": "Constructing SQL queries using fmt.Sprintf or string concatenation allows SQL injection. Pass arguments directly to db.Query/db.Exec using SQL placeholders ($1, ?).",
                    "line_number": line_no,
                })
            elif "fmt.Sprintf" in fn_text:
                if any(k in args_text.lower() for k in ("select ", "insert ", "update ", "delete ")):
                    findings.append({
                        "category": "Security",
                        "file": rel_path,
                        "title": "Unsafe dynamic SQL query construction in Go",
                        "severity": "High",
                        "suggestion": "Constructing SQL queries using fmt.Sprintf or string concatenation allows SQL injection. Pass arguments directly to db.Query/db.Exec using SQL placeholders ($1, ?).",
                        "line_number": line_no,
                    })

        for child in node.children:
            visitor(child)

    visitor(root_node)
    return findings


class TreeSitterScanner:
    """Production Tree-Sitter AST Scanner for JavaScript, TypeScript, Java, and Go."""

    @staticmethod
    def is_available() -> bool:
        return HAS_TREE_SITTER and bool(_PARSERS)

    @staticmethod
    def scan_code(rel_path: str, content: str, ext: str) -> list[dict]:
        findings: list[dict] = []
        ext_clean = ext.lower().lstrip(".")

        # 1. Global Secret Scanning across file
        for pattern, title, severity, suggestion in SECRET_PATTERNS:
            match = pattern.search(content)
            if match:
                line_no = content[:match.start()].count("\n") + 1
                findings.append({
                    "category": "Security",
                    "file": rel_path,
                    "title": title,
                    "severity": severity,
                    "suggestion": suggestion,
                    "line_number": line_no,
                })

        if not HAS_TREE_SITTER:
            return findings

        # Pick appropriate parser
        parser = None
        if ext_clean in ("js", "jsx"):
            parser = _PARSERS.get("js")
        elif ext_clean == "ts":
            parser = _PARSERS.get("ts")
        elif ext_clean == "tsx":
            parser = _PARSERS.get("tsx")
        elif ext_clean == "java":
            parser = _PARSERS.get("java")
        elif ext_clean == "go":
            parser = _PARSERS.get("go")

        if not parser:
            return findings

        try:
            code_bytes = content.encode("utf-8")
            tree = parser.parse(code_bytes)
            root = tree.root_node

            if ext_clean in ("js", "jsx", "ts", "tsx"):
                ast_findings = _scan_js_ts_ast(root, rel_path, code_bytes)
            elif ext_clean == "java":
                ast_findings = _scan_java_ast(root, rel_path, code_bytes)
            elif ext_clean == "go":
                ast_findings = _scan_go_ast(root, rel_path, code_bytes)
            else:
                ast_findings = []

            # Deduplicate by line_number and title
            seen = set()
            for f in ast_findings:
                key = (f["line_number"], f["title"])
                if key not in seen:
                    seen.add(key)
                    findings.append(f)

        except Exception:
            pass

        return findings
