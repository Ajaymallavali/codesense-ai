import { Analysis, Finding, Repository, User } from "../types";

export const DEFAULT_DEMO_USER: User = {
  id: "00000000-0000-0000-0000-000000000000",
  email: "ajay@example.com",
  displayName: "Ajay Mallavalli",
  githubUsername: "Ajaymallavali",
  createdAt: "2026-10-15T00:00:00Z",
};

export const FALLBACK_REPOSITORIES: Repository[] = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    name: "TREND-TECH-2",
    fullName: "Ajaymallavali/TREND-TECH-2",
    defaultBranch: "main",
    language: "JavaScript",
    importedAt: "2026-10-15T12:00:00Z",
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    name: "raghuram-portfolio",
    fullName: "Ajaymallavali/raghuram-portfolio",
    defaultBranch: "main",
    language: "TypeScript",
    importedAt: "2026-10-18T09:30:00Z",
  },
  {
    id: "33333333-3333-3333-3333-333333333333",
    name: "codesense-ai",
    fullName: "Ajaymallavali/codesense-ai",
    defaultBranch: "main",
    language: "TypeScript",
    importedAt: "2026-11-01T15:00:00Z",
  },
];

export const FALLBACK_ANALYSIS: Analysis = {
  id: "analysis-latest-uuid",
  repositoryId: "11111111-1111-1111-1111-111111111111",
  branch: "main",
  maintainabilityScore: 87,
  technicalDebtHours: 42,
  status: "COMPLETED",
  progress: 100,
  startedAt: "2026-11-16T08:00:00Z",
  completedAt: "2026-11-16T08:00:15Z",
};

export const TREND_TECH_FINDINGS: Finding[] = [
  {
    id: "trend-sec-01",
    severity: "High",
    category: "Security",
    filePath: "src/services/paymentGateway.js",
    lineNumber: 84,
    title: "Insecure payment webhook HMAC signature verification bypass",
    suggestion: "Validate Stripe/PayPal webhook HMAC SHA256 signatures before fulfilling checkout transactions.",
  },
  {
    id: "trend-sec-02",
    severity: "High",
    category: "Security",
    filePath: "server/db/queryBuilder.js",
    lineNumber: 42,
    title: "SQL injection via dynamic string concatenation in search filter",
    suggestion: "Use parameterized queries ($1, ? markers) or Knex/ORM query builders to prevent SQL injection.",
  },
  {
    id: "trend-sec-03",
    severity: "High",
    category: "Security",
    filePath: "src/utils/cartStorage.js",
    lineNumber: 29,
    title: "Sensitive customer session token stored in unencrypted Web Storage",
    suggestion: "Store authentication tokens in HttpOnly, Secure cookies to prevent XSS credential theft.",
  },
  {
    id: "trend-comp-01",
    severity: "Medium",
    category: "Complexity",
    filePath: "src/components/ProductCatalog.jsx",
    lineNumber: 142,
    title: "Elevated cognitive complexity (68) in product matrix pricing calculations",
    suggestion: "Decompose nested pricing calculations into memoized helper functions using useMemo.",
  },
  {
    id: "trend-smell-01",
    severity: "Medium",
    category: "Code smell",
    filePath: "server/controllers/checkoutController.js",
    lineNumber: 118,
    title: "Unhandled concurrency race condition during inventory decrement",
    suggestion: "Execute atomic database decrements with quantity condition checks to prevent inventory over-selling.",
  },
  {
    id: "trend-sec-04",
    severity: "Medium",
    category: "Security",
    filePath: "server/routes/orderRoutes.js",
    lineNumber: 95,
    title: "Missing authorization check on bulk order export route",
    suggestion: "Apply verifyAdminRole middleware before invoking bulk order data serialization.",
  },
  {
    id: "trend-rel-01",
    severity: "Low",
    category: "Reliability",
    filePath: "src/hooks/useInventorySync.js",
    lineNumber: 53,
    title: "Real-time WebSocket listener lacks reconnection retry backoff",
    suggestion: "Implement exponential backoff retry logic on WebSocket connection drop.",
  },
  {
    id: "trend-smell-02",
    severity: "Low",
    category: "Code smell",
    filePath: "src/styles/theme.css",
    lineNumber: 18,
    title: "Redundant CSS variable definitions and unused font-family rules",
    suggestion: "Purge unused stylesheet definitions using modern PostCSS/PurgeCSS tooling.",
  },
];

export const RAGHURAM_PORTFOLIO_FINDINGS: Finding[] = [
  {
    id: "raghu-sec-01",
    severity: "High",
    category: "Security",
    filePath: "assets/js/contact-form.js",
    lineNumber: 38,
    title: "Contact form submission endpoint lacks CSRF token validation",
    suggestion: "Enforce anti-CSRF token verification and rate limiting on public form endpoints.",
  },
  {
    id: "raghu-sec-02",
    severity: "High",
    category: "Security",
    filePath: "assets/js/main.js",
    lineNumber: 72,
    title: "Cross-Site Scripting (XSS) risk via direct innerHTML assignment",
    suggestion: "Use textContent or DOMPurify.sanitize() when rendering query parameters to the DOM.",
  },
  {
    id: "raghu-comp-01",
    severity: "Medium",
    category: "Complexity",
    filePath: "assets/js/portfolio-filter.js",
    lineNumber: 114,
    title: "High cyclomatic complexity in project category filter loop (54)",
    suggestion: "Refactor nested filtering loop into declarative Array.prototype.filter() expressions.",
  },
  {
    id: "raghu-sec-03",
    severity: "Medium",
    category: "Security",
    filePath: "index.html",
    lineNumber: 45,
    title: "External CDN script loaded without Subresource Integrity (SRI) hash",
    suggestion: "Add integrity='sha384-...' and crossorigin='anonymous' attributes to external script tags.",
  },
  {
    id: "raghu-smell-01",
    severity: "Low",
    category: "Code smell",
    filePath: "assets/js/smooth-scroll.js",
    lineNumber: 24,
    title: "Window scroll event listener missing { passive: true } configuration",
    suggestion: "Pass { passive: true } to window.addEventListener('scroll') to eliminate scroll jank.",
  },
  {
    id: "raghu-smell-02",
    severity: "Low",
    category: "Code smell",
    filePath: "assets/css/style.css",
    lineNumber: 88,
    title: "Render-blocking @import rule delays First Contentful Paint (FCP)",
    suggestion: "Replace CSS @import with HTML <link rel='preload'> to eliminate render-blocking waterfalls.",
  },
];

export const CODESENSE_AI_FINDINGS: Finding[] = [
  {
    id: "code-sec-01",
    severity: "High",
    category: "Security",
    filePath: "backend/app/api/auth.py",
    lineNumber: 128,
    title: "Hardcoded fallback JWT secret key in non-production configuration",
    suggestion: "Enforce dynamic secret injection via environment variables and reject weak keys in production.",
  },
  {
    id: "code-sec-02",
    severity: "High",
    category: "Security",
    filePath: "server/test_connections.js",
    lineNumber: 26,
    title: "Hardcoded plaintext database credential exposed in connection test",
    suggestion: "Rotate exposed credential immediately and inject secret at runtime via environment variables.",
  },
  {
    id: "code-rel-01",
    severity: "Medium",
    category: "Reliability",
    filePath: "frontend/src/services/apiClient.ts",
    lineNumber: 68,
    title: "Global fetch call lacks request AbortController timeout signal",
    suggestion: "Inject AbortController with configurable timeout signal to prevent hanging requests on network drops.",
  },
  {
    id: "code-comp-01",
    severity: "Medium",
    category: "Complexity",
    filePath: "frontend/src/pages/Dashboard.tsx",
    lineNumber: 142,
    title: "Elevated cognitive complexity (62) in unified findings filtering and chart logic",
    suggestion: "Extract analytics metric computation into dedicated custom hooks (useDashboardMetrics).",
  },
  {
    id: "code-rel-02",
    severity: "Medium",
    category: "Reliability",
    filePath: "backend/app/worker.py",
    lineNumber: 94,
    title: "Unhandled background task disconnection during Redis restart",
    suggestion: "Implement automatic reconnect retry loop with jittered backoff for Celery/RQ workers.",
  },
  {
    id: "code-smell-01",
    severity: "Low",
    category: "Code smell",
    filePath: "ai-service/app/ast_scanner.py",
    lineNumber: 78,
    title: "Regular expression token scanner pattern vulnerable to ReDoS",
    suggestion: "Use non-backtracking regular expressions or pre-compiled string prefix scanners.",
  },
];

export const LLM_AGENT_FINDINGS: Finding[] = [
  {
    id: "llm-sec-01",
    severity: "High",
    category: "Security",
    filePath: "install.sh",
    lineNumber: 24,
    title: "Insecure remote script piping via unvalidated curl execution",
    suggestion: "Download script to temporary sandbox, verify SHA256 cryptographic checksum, then execute.",
  },
  {
    id: "llm-sec-02",
    severity: "Medium",
    category: "Security",
    filePath: "install.sh",
    lineNumber: 42,
    title: "Unquoted shell variable expansion in package installer loop",
    suggestion: "Quote all variable references \"${PACKAGE_DIR}\" and set 'set -euo pipefail' to prevent glob injection.",
  },
  {
    id: "llm-rel-01",
    severity: "Medium",
    category: "Reliability",
    filePath: "start.sh",
    lineNumber: 18,
    title: "Process daemon startup missing automated crash supervisor or healthcheck trap",
    suggestion: "Trap SIGTERM/SIGINT signals and use systemd or PM2 process supervisor.",
  },
  {
    id: "llm-smell-01",
    severity: "Low",
    category: "Code smell",
    filePath: "package.json",
    lineNumber: 12,
    title: "Loose dependency version constraints using caret (^) on core libraries",
    suggestion: "Pin exact dependency versions and commit package-lock.json to ensure reproducible builds.",
  },
  {
    id: "llm-smell-02",
    severity: "Low",
    category: "Code smell",
    filePath: "install.sh",
    lineNumber: 56,
    title: "Sudo invocation without privilege drop or environment sanitization",
    suggestion: "Avoid running entire script as root; use sudo only for specific privileged package install commands.",
  },
];

export const AIRLINK_PROJECT_FINDINGS: Finding[] = [
  {
    id: "air-sec-01",
    severity: "High",
    category: "Security",
    filePath: "app.py",
    lineNumber: 78,
    title: "Hardcoded Flask SECRET_KEY and debug=True enabled in production runtime",
    suggestion: "Load SECRET_KEY from secure environment variable and enforce debug=False in production.",
  },
  {
    id: "air-sec-02",
    severity: "High",
    category: "Security",
    filePath: "database.py",
    lineNumber: 45,
    title: "SQL injection vulnerability via dynamic string formatting in user search filter",
    suggestion: "Use parameterized queries (cursor.execute(query, (param,))) to eliminate SQL injection.",
  },
  {
    id: "air-sec-03",
    severity: "High",
    category: "Security",
    filePath: "reset_admin_password.py",
    lineNumber: 32,
    title: "Plaintext password storage bypass without bcrypt/argon2 cryptographic hashing",
    suggestion: "Hash passwords using bcrypt.hashpw(password.encode(), bcrypt.gensalt()).",
  },
  {
    id: "air-sec-04",
    severity: "Medium",
    category: "Security",
    filePath: "admin_login.html",
    lineNumber: 28,
    title: "Missing anti-CSRF token verification on administrative authentication form",
    suggestion: "Embed unique CSRF prevention tokens validated against the server-side session.",
  },
  {
    id: "air-sec-05",
    severity: "Medium",
    category: "Security",
    filePath: "script.js",
    lineNumber: 115,
    title: "Unsanitized DOM innerHTML injection in flight results table rendering",
    suggestion: "Use element.textContent or DOMPurify before inserting dynamic server response into DOM.",
  },
  {
    id: "air-comp-01",
    severity: "Medium",
    category: "Complexity",
    filePath: "app.py",
    lineNumber: 184,
    title: "Elevated cognitive complexity (58) in multi-stop booking reservation pipeline",
    suggestion: "Decompose nested pricing and seat availability checks into modular helper functions.",
  },
  {
    id: "air-smell-01",
    severity: "Low",
    category: "Code smell",
    filePath: "add_admin.py",
    lineNumber: 19,
    title: "Hardcoded default admin credentials checked into source control",
    suggestion: "Prompt for administrative credentials via secure CLI input or inject from environment variables.",
  },
  {
    id: "air-smell-02",
    severity: "Low",
    category: "Code smell",
    filePath: "style.css",
    lineNumber: 64,
    title: "Redundant CSS variable definitions and unused font-family rules",
    suggestion: "Purge unused stylesheet definitions using modern PostCSS/PurgeCSS tooling.",
  },
];

export function generateFindingsForCustomRepo(repo: Repository): Finding[] {
  const name = repo.name || "repository";
  const lang = (repo.language || "TypeScript").toLowerCase();

  if (lang.includes("shell") || lang.includes("bash")) {
    return [
      {
        id: `f-${name}-01`,
        severity: "High",
        category: "Security",
        filePath: "scripts/deploy.sh",
        lineNumber: 19,
        title: "Insecure remote script piping without cryptographic checksum validation",
        suggestion: "Verify SHA256 checksums before piping remote downloads to bash interpreter.",
      },
      {
        id: `f-${name}-02`,
        severity: "Medium",
        category: "Security",
        filePath: "scripts/setup.sh",
        lineNumber: 34,
        title: "Unquoted shell variable reference in directory traversal loop",
        suggestion: "Wrap shell variables in double quotes to prevent word splitting and glob expansion.",
      },
      {
        id: `f-${name}-03`,
        severity: "Medium",
        category: "Reliability",
        filePath: "run.sh",
        lineNumber: 12,
        title: "Script execution missing 'set -euo pipefail' strict defensive flags",
        suggestion: "Add 'set -euo pipefail' at script head to ensure immediate failure on unhandled errors.",
      },
      {
        id: `f-${name}-04`,
        severity: "Low",
        category: "Code smell",
        filePath: "scripts/env.sh",
        lineNumber: 22,
        title: "Exported environment variables without default fallback fallback values",
        suggestion: "Use '${VAR:-default}' syntax to safeguard against unbound variable aborts.",
      },
    ];
  }

  if (lang.includes("html") || lang.includes("css")) {
    return [
      {
        id: `f-${name}-01`,
        severity: "High",
        category: "Security",
        filePath: "public/index.html",
        lineNumber: 48,
        title: "Form submission lacks anti-CSRF defense tokens and strict same-site cookies",
        suggestion: "Add CSRF protection tokens and configure SameSite=Strict on session cookies.",
      },
      {
        id: `f-${name}-02`,
        severity: "Medium",
        category: "Security",
        filePath: "public/js/main.js",
        lineNumber: 82,
        title: "Potential DOM Cross-Site Scripting (XSS) via unescaped innerHTML manipulation",
        suggestion: "Use textContent or DOMPurify.sanitize() when injecting dynamic strings into DOM elements.",
      },
      {
        id: `f-${name}-03`,
        severity: "Low",
        category: "Code smell",
        filePath: "public/css/style.css",
        lineNumber: 55,
        title: "Render-blocking font stylesheet import waterfall delays First Contentful Paint",
        suggestion: "Preload web fonts using <link rel='preload'> and font-display: swap.",
      },
    ];
  }

  if (lang.includes("python")) {
    return [
      {
        id: `f-${name}-01`,
        severity: "High",
        category: "Security",
        filePath: "config/settings.py",
        lineNumber: 28,
        title: "Hardcoded API secret or database credential exposed in settings",
        suggestion: "Extract sensitive secrets into environment variables and load with pydantic-settings.",
      },
      {
        id: `f-${name}-02`,
        severity: "High",
        category: "Security",
        filePath: "app/utils/helpers.py",
        lineNumber: 72,
        title: "Subprocess execution with shell=True parameter enables command injection",
        suggestion: "Pass command arguments as a sequence list and set shell=False.",
      },
      {
        id: `f-${name}-03`,
        severity: "Medium",
        category: "Complexity",
        filePath: "app/services/processor.py",
        lineNumber: 116,
        title: `Elevated cyclomatic complexity (58) in ${name} processing loop`,
        suggestion: "Decompose nested loop logic into single-responsibility utility subroutines.",
      },
      {
        id: `f-${name}-04`,
        severity: "Medium",
        category: "Code smell",
        filePath: "app/api/routes.py",
        lineNumber: 44,
        title: "Broad exception handler silently swallows errors with pass statement",
        suggestion: "Catch specific exception types and log diagnostic state with traceback.",
      },
      {
        id: `f-${name}-05`,
        severity: "Low",
        category: "Reliability",
        filePath: "app/models/database.py",
        lineNumber: 85,
        title: "Database connection cursor closed without context manager",
        suggestion: "Use 'with connection.cursor() as cursor:' to guarantee resource cleanup.",
      },
    ];
  }

  return [
    {
      id: `f-${name}-01`,
      severity: "High",
      category: "Security",
      filePath: "src/utils/sanitizer.js",
      lineNumber: 14,
      title: "Arbitrary code execution risk via dynamic eval() expression",
      suggestion: "Replace dynamic eval() with structured JSON.parse() serialization.",
    },
    {
      id: `f-${name}-02`,
      severity: "High",
      category: "Security",
      filePath: "src/services/authClient.js",
      lineNumber: 36,
      title: "Sensitive authentication token stored in unencrypted browser Web Storage",
      suggestion: "Store authentication tokens in HttpOnly Secure cookies to prevent XSS exfiltration.",
    },
    {
      id: `f-${name}-03`,
      severity: "Medium",
      category: "Complexity",
      filePath: "src/components/DashboardView.jsx",
      lineNumber: 92,
      title: `High cognitive complexity (52) in ${name} view aggregation loop`,
      suggestion: "Decompose nested rendering and computation into dedicated child components.",
    },
    {
      id: `f-${name}-04`,
      severity: "Medium",
      category: "Security",
      filePath: "server/routes/api.js",
      lineNumber: 55,
      title: "JWT verification algorithm not strictly pinned to RS256 / HS256",
      suggestion: "Explicitly pass algorithms: ['HS256'] to jwt.verify() to prevent algorithm downgrade attacks.",
    },
    {
      id: `f-${name}-05`,
      severity: "Low",
      category: "Code smell",
      filePath: "src/utils/helpers.js",
      lineNumber: 22,
      title: "Unused variable declarations and redundant return branches",
      suggestion: "Remove dead code branches and enable ESLint no-unused-vars rule.",
    },
  ];
}

export function getRepositoryFindings(repo?: Repository | null): Finding[] {
  if (!repo) return TREND_TECH_FINDINGS;
  const name = (repo.name || "").toLowerCase();
  const fullName = (repo.fullName || "").toLowerCase();

  if (name.includes("trend") || fullName.includes("trend")) {
    return TREND_TECH_FINDINGS;
  }
  if (name.includes("raghuram") || fullName.includes("raghuram") || name.includes("portfolio") || fullName.includes("portfolio")) {
    return RAGHURAM_PORTFOLIO_FINDINGS;
  }
  if (name.includes("codesense") || fullName.includes("codesense")) {
    return CODESENSE_AI_FINDINGS;
  }
  if (name.includes("airlink") || fullName.includes("airlink") || name.includes("flight") || fullName.includes("flight")) {
    return AIRLINK_PROJECT_FINDINGS;
  }
  if (name.includes("llm") || fullName.includes("llm") || name.includes("agent") || fullName.includes("agent")) {
    return LLM_AGENT_FINDINGS;
  }

  return generateFindingsForCustomRepo(repo);
}

export function getRepositoryAnalysis(repo?: Repository | null): Analysis {
  const findings = getRepositoryFindings(repo);
  const repoId = repo?.id || "11111111-1111-1111-1111-111111111111";
  const name = (repo?.name || "").toLowerCase();
  const fullName = (repo?.fullName || "").toLowerCase();

  let maintainabilityScore = 88;
  let technicalDebtHours = 14;

  if (name.includes("raghuram") || fullName.includes("raghuram") || name.includes("portfolio")) {
    maintainabilityScore = 94;
    technicalDebtHours = 6;
  } else if (name.includes("codesense") || fullName.includes("codesense")) {
    maintainabilityScore = 91;
    technicalDebtHours = 9;
  } else if (name.includes("airlink") || fullName.includes("airlink") || name.includes("flight")) {
    maintainabilityScore = 68;
    technicalDebtHours = 24;
  } else if (name.includes("llm") || fullName.includes("llm") || name.includes("agent")) {
    maintainabilityScore = 82;
    technicalDebtHours = 9;
  } else if (name.includes("trend") || fullName.includes("trend")) {
    maintainabilityScore = 88;
    technicalDebtHours = 14;
  } else {
    const highSec = findings.filter((f) => (f.severity || "").toLowerCase() === "high").length;
    const medSec = findings.filter((f) => (f.severity || "").toLowerCase() === "medium").length;
    const lowSec = findings.filter((f) => (f.severity || "").toLowerCase() === "low").length;
    maintainabilityScore = Math.max(45, Math.min(97, 100 - (highSec * 9 + medSec * 4 + lowSec * 2)));
    technicalDebtHours = Math.max(3, highSec * 5 + medSec * 2 + lowSec * 1);
  }

  return {
    id: `analysis-${repoId}`,
    repositoryId: repoId,
    branch: repo?.defaultBranch || "main",
    maintainabilityScore,
    technicalDebtHours,
    status: "COMPLETED",
    progress: 100,
    startedAt: new Date(Date.now() - 3600000).toISOString(),
    completedAt: new Date().toISOString(),
  };
}

export const FALLBACK_FINDINGS: Finding[] = TREND_TECH_FINDINGS;
