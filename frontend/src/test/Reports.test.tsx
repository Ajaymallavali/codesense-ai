import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReportsPage } from "../pages/Reports";
import { Repository, ReportSummary } from "../types";
import { reportApi } from "../services/reportApi";

vi.mock("../services/reportApi", () => ({
  reportApi: {
    getSummary: vi.fn(),
    generatePdfReport: vi.fn(),
    downloadReport: vi.fn(),
  },
}));

const mockRepo: Repository = {
  id: "repo-999",
  name: "spring-commerce-api",
  fullName: "org/spring-commerce-api",
  defaultBranch: "main",
  language: "Java",
  importedAt: "2026-10-15T12:00:00Z",
};

const mockSummary: ReportSummary = {
  repository: "org/spring-commerce-api",
  branch: "main",
  language: "Java",
  analysisId: "a-123",
  completedAt: "2026-10-15T12:05:00Z",
  maintainabilityScore: 88,
  technicalDebtHours: 4.5,
  findingsCount: 3,
  findingsByCategory: { Security: 1, Maintainability: 2 },
  findings: [
    {
      id: "f-1",
      filePath: "src/main/App.java",
      lineNumber: 10,
      category: "Security",
      severity: "High",
      title: "Hardcoded secret detected",
      suggestion: "Rotate secret",
    },
  ],
};

describe("ReportsPage Component", () => {
  it("shows prompt when no active repo is selected", () => {
    render(<ReportsPage activeRepo={null} />);
    expect(screen.getByText(/please select an imported repository/i)).toBeInTheDocument();
  });

  it("renders report export cards when repository is selected", async () => {
    vi.mocked(reportApi.getSummary).mockResolvedValue(mockSummary);
    render(<ReportsPage activeRepo={mockRepo} />);

    expect(screen.getByText("Compiled Code Health Reports")).toBeInTheDocument();
    expect(await screen.findByText("Full Quality and Security Assessment Report")).toBeInTheDocument();
    expect(screen.getByText("Technical Debt Analysis and Remediation Plan")).toBeInTheDocument();

    const pdfButtons = screen.getAllByRole("button", { name: /download pdf/i });
    expect(pdfButtons.length).toBe(2);

    const markdownButtons = screen.getAllByRole("button", { name: /markdown/i });
    expect(markdownButtons.length).toBe(2);
  });
});
