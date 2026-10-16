import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { Dashboard } from "../pages/Dashboard";
import { Repository, Analysis, Finding } from "../types";
import { analysisApi } from "../services/analysisApi";

vi.mock("../services/analysisApi", () => ({
  analysisApi: {
    getAnalysisHistory: vi.fn().mockResolvedValue([]),
    getLatestAnalysis: vi.fn().mockResolvedValue(null),
    triggerAnalysis: vi.fn(),
    getFindings: vi.fn().mockResolvedValue([]),
  },
}));

const mockRepo: Repository = {
  id: "repo-123",
  name: "fastapi-review-engine",
  fullName: "codesense/fastapi-review-engine",
  defaultBranch: "main",
  language: "Python",
  importedAt: "2026-10-15T12:00:00Z",
};

const mockAnalysis: Analysis = {
  id: "analysis-123",
  repositoryId: "repo-123",
  branch: "main",
  maintainabilityScore: 91,
  technicalDebtHours: 8,
  status: "COMPLETED",
  progress: 100,
  startedAt: "2026-10-15T12:00:00Z",
  completedAt: "2026-10-15T12:02:00Z",
};

const mockFindings: Finding[] = [
  {
    id: "f-1",
    category: "Security",
    severity: "High",
    filePath: "app/auth.py",
    title: "Hardcoded secret detected",
    suggestion: "Use environment variables",
    lineNumber: 42,
  },
  {
    id: "f-2",
    category: "Complexity",
    severity: "Medium",
    filePath: "app/scanner.py",
    title: "High cognitive complexity (18)",
    suggestion: "Extract subroutine",
    lineNumber: 15,
  },
];

describe("Dashboard Page Component", () => {
  it("renders empty state when no active repository is selected", () => {
    render(
      <Dashboard
        activeRepo={null}
        latestAnalysis={null}
        findingsList={[]}
        isLoadingAnalysis={false}
        onTriggerAnalysis={vi.fn()}
        onNavigateToReview={vi.fn()}
        onOpenImportModal={vi.fn()}
      />
    );

    expect(screen.getByText(/no repository selected/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /import repository/i })).toBeInTheDocument();
  });

  it("renders repository banner, scorecards, and findings when repo is active", async () => {
    render(
      <Dashboard
        activeRepo={mockRepo}
        latestAnalysis={mockAnalysis}
        findingsList={mockFindings}
        isLoadingAnalysis={false}
        onTriggerAnalysis={vi.fn()}
        onNavigateToReview={vi.fn()}
        onOpenImportModal={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("codesense/fastapi-review-engine")).toBeInTheDocument();
      expect(screen.getByText("91/100")).toBeInTheDocument();
      expect(screen.getByText("8 hrs")).toBeInTheDocument();
      expect(screen.getByText("Hardcoded secret detected")).toBeInTheDocument();
    });
  });
});
