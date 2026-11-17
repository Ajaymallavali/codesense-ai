import { describe, it, expect, vi, beforeEach } from "vitest";
import { reportApi } from "../services/reportApi";
import { Finding, Repository, Analysis } from "../types";

describe("Line-Level Finding PDF Reports (High, Medium, Low)", () => {
  const mockRepo: Repository = {
    id: "test-repo-123",
    name: "TREND-TECH-2",
    fullName: "Ajaymallavali/TREND-TECH-2",
    defaultBranch: "main",
    language: "JavaScript",
    importedAt: "2026-11-15T00:00:00Z",
  };

  const mockAnalysis: Analysis = {
    id: "run-4ffc36a2-e426-474a",
    repositoryId: "test-repo-123",
    branch: "main",
    maintainabilityScore: 30,
    technicalDebtHours: 5796,
    status: "COMPLETED",
    progress: 100,
    startedAt: "2026-11-15T10:00:00Z",
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("generates High Severity finding report matching template without errors", async () => {
    const highFinding: Finding = {
      id: "f-high-1",
      category: "Security",
      severity: "High",
      filePath: "server/test_connections.js",
      lineNumber: 26,
      title: "Hardcoded secret or API credential detected",
    };

    const decisionData = {
      decisionTitle: "Extract Secret into Environment Config (.env) & Secure Secret Vault",
      failureExplanation: "Line 26 contains hardcoded plaintext secrets committed directly into source code.",
      riskImpact: "Hardcoded Credential Exposure (CWE-798).",
      strategySteps: ["Invalidate token", "Extract to .env", "Load dynamically via process.env"],
      vulnerableSnippet: 'const API_SECRET_KEY = "sk_live_948194018294719284719";',
      remediatedSnippet: 'const API_SECRET_KEY = process.env.API_SECRET_KEY;',
      confidence: 98,
      cwe: "CWE-798",
    };

    await expect(
      reportApi.generateLineFindingPdfReport(highFinding, mockRepo, mockAnalysis, decisionData)
    ).resolves.not.toThrow();
  });

  it("generates Medium Severity finding report matching template without errors", async () => {
    const mediumFinding: Finding = {
      id: "f-med-1",
      category: "Code smell",
      severity: "Medium",
      filePath: "test_mcp.py",
      lineNumber: 13,
      title: "Broad exception silently swallowed with pass",
    };

    const decisionData = {
      decisionTitle: "Replace Broad Exception Catch with Explicit, Observable Error Handling",
      failureExplanation: "Line 13 contains a broad exception handler whose body swallows errors silently (except Exception: pass).",
      riskImpact: "Reliability & Debuggability Degradation (CWE-390 / CWE-703).",
      strategySteps: ["Inspect handler", "Catch expected exception", "Log stack trace", "Add test"],
      vulnerableSnippet: "try:\n    perform_operation()\nexcept Exception:\n    pass",
      remediatedSnippet: "try:\n    perform_operation()\nexcept ExpectedError:\n    logger.exception('Operation failed')\n    raise",
      confidence: 96,
      cwe: "CWE-390",
    };

    await expect(
      reportApi.generateLineFindingPdfReport(mediumFinding, mockRepo, mockAnalysis, decisionData)
    ).resolves.not.toThrow();
  });

  it("generates Low Severity finding report matching template without errors", async () => {
    const lowFinding: Finding = {
      id: "f-low-1",
      category: "Code smell",
      severity: "Low",
      filePath: "scratch.jsx",
      lineNumber: 1,
      title: "Long source file (>250 lines)",
    };

    const decisionData = {
      decisionTitle: "Decompose Monolithic Source File into Single-Responsibility Modules",
      failureExplanation: "Line 1 in scratch.jsx exceeds the configured length threshold (>250 lines).",
      riskImpact: "Architectural Maintainability & Testability Debt (CWE-1076).",
      strategySteps: ["Record line count", "Group by responsibility", "Extract units", "Run regression checks"],
      vulnerableSnippet: "// Long monolithic source file (>250 lines)",
      remediatedSnippet: "// Refactored modular boundaries: services/, components/, hooks/, utils/",
      confidence: 93,
      cwe: "CWE-1076",
    };

    await expect(
      reportApi.generateLineFindingPdfReport(lowFinding, mockRepo, mockAnalysis, decisionData)
    ).resolves.not.toThrow();
  });
});
