import React, { useEffect, useState } from "react";
import { Download, FileText, Printer, ShieldCheck, AlertTriangle, RefreshCw } from "lucide-react";
import { ReportSummary, Repository } from "../types";
import { reportApi } from "../services/reportApi";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Loader } from "../components/Loader";

interface ReportsPageProps {
  activeRepo: Repository | null;
}

export function ReportsPage({ activeRepo }: ReportsPageProps) {
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState("");

  useEffect(() => {
    if (!activeRepo) return;
    setIsLoading(true);
    reportApi
      .getSummary(activeRepo.id)
      .then((data) => setSummary(data))
      .catch((err) => console.error("Error fetching report summary:", err))
      .finally(() => setIsLoading(false));
  }, [activeRepo]);

  async function handleDownloadPdf(type: "assessment" | "debt") {
    if (!summary) return;
    setIsDownloading(true);
    setDownloadSuccess("");
    try {
      await reportApi.generatePdfReport(summary, type);
      setDownloadSuccess(
        `PDF Report '${type === "debt" ? "Technical Debt Plan" : "Quality Assessment"}' generated!`
      );
      setTimeout(() => setDownloadSuccess(""), 4000);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to generate PDF report.");
    } finally {
      setIsDownloading(false);
    }
  }

  async function handleDownloadMarkdown(type: "assessment" | "debt") {
    if (!activeRepo) return;
    setIsDownloading(true);
    setDownloadSuccess("");
    try {
      await reportApi.downloadReport(activeRepo.id, type);
      setDownloadSuccess(
        `Markdown Report '${type === "debt" ? "Technical Debt Plan" : "Quality Assessment"}' downloaded!`
      );
      setTimeout(() => setDownloadSuccess(""), 4000);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to download report.");
    } finally {
      setIsDownloading(false);
    }
  }

  function handlePrint(type: "quality" | "debt") {
    if (!summary) return;
    reportApi.printReport(summary, type);
  }

  if (!activeRepo) {
    return (
      <Card className="text-center py-12">
        <p className="text-sm text-slate-500">Please select an imported repository to view and export reports.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overview Card */}
      <div className="rounded border border-slate-200 bg-white p-5 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900">Compiled Code Health Reports</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Export authoritative AST security audits and technical debt assessments for{" "}
            <strong className="text-slate-800">{activeRepo.fullName || activeRepo.name}</strong>.
          </p>
        </div>
        {summary && (
          <div className="flex items-center gap-3 text-xs bg-slate-50 border border-slate-200 px-3 py-1.5 rounded">
            <span className="font-semibold text-teal-800">Score: {summary.maintainabilityScore}/100</span>
            <span className="text-slate-300">|</span>
            <span className="text-slate-600">Debt: {summary.technicalDebtHours}h</span>
            <span className="text-slate-300">|</span>
            <span className="text-slate-600">Findings: {summary.findingsCount}</span>
          </div>
        )}
      </div>

      {downloadSuccess && (
        <div className="rounded border border-emerald-200 bg-emerald-50 p-3 text-xs font-semibold text-emerald-800">
          ✓ {downloadSuccess}
        </div>
      )}

      {isLoading ? (
        <Loader message="Loading compiled reports from database..." />
      ) : (
        <div className="space-y-4">
          {/* Report 1: Full Quality & Security Assessment */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between rounded border border-slate-200 bg-white p-5 hover:bg-slate-50/60 transition gap-4 shadow-sm">
            <div className="flex items-start gap-3.5">
              <div className="rounded bg-rose-50 border border-rose-200 p-2.5 text-rose-700 mt-0.5">
                <ShieldCheck size={22} />
              </div>
              <div>
                <h3 className="font-bold text-sm text-slate-900">
                  Full Quality and Security Assessment Report
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  {activeRepo.fullName || activeRepo.name} | branch: {activeRepo.defaultBranch}
                </p>
                <p className="text-[11px] text-slate-400 mt-1">
                  Includes AST static checks, vulnerability severity breakdown, and architectural complexity scores.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <Button
                variant="outline"
                size="sm"
                icon={<Printer size={14} />}
                onClick={() => handlePrint("quality")}
                disabled={!summary}
              >
                Print View
              </Button>
              <Button
                variant="outline"
                size="sm"
                icon={<FileText size={14} />}
                onClick={() => handleDownloadMarkdown("assessment")}
                disabled={!summary}
              >
                Markdown
              </Button>
              <Button
                variant="primary"
                size="sm"
                icon={<Download size={14} />}
                onClick={() => handleDownloadPdf("assessment")}
                disabled={!summary}
                isLoading={isDownloading}
              >
                Download PDF
              </Button>
            </div>
          </div>

          {/* Report 2: Technical Debt & Remediation Plan */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between rounded border border-slate-200 bg-white p-5 hover:bg-slate-50/60 transition gap-4 shadow-sm">
            <div className="flex items-start gap-3.5">
              <div className="rounded bg-amber-50 border border-amber-200 p-2.5 text-amber-700 mt-0.5">
                <AlertTriangle size={22} />
              </div>
              <div>
                <h3 className="font-bold text-sm text-slate-900">
                  Technical Debt Analysis and Remediation Plan
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  {activeRepo.fullName || activeRepo.name} | branch: {activeRepo.defaultBranch}
                </p>
                <p className="text-[11px] text-slate-400 mt-1">
                  Prioritized backlog of refactorings, cognitive complexity hotspots, and remediation effort estimates.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <Button
                variant="outline"
                size="sm"
                icon={<Printer size={14} />}
                onClick={() => handlePrint("debt")}
                disabled={!summary}
              >
                Print View
              </Button>
              <Button
                variant="outline"
                size="sm"
                icon={<FileText size={14} />}
                onClick={() => handleDownloadMarkdown("debt")}
                disabled={!summary}
              >
                Markdown
              </Button>
              <Button
                variant="primary"
                size="sm"
                icon={<Download size={14} />}
                onClick={() => handleDownloadPdf("debt")}
                disabled={!summary}
                isLoading={isDownloading}
              >
                Download PDF
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
