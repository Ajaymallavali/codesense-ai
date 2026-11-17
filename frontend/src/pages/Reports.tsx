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
    } catch {
      try {
        if (activeRepo) {
          await reportApi.downloadReport(activeRepo.id, type, "pdf");
        }
        setDownloadSuccess(
          `PDF Report '${type === "debt" ? "Technical Debt Plan" : "Quality Assessment"}' generated!`
        );
        setTimeout(() => setDownloadSuccess(""), 4000);
      } catch (clientErr) {
        alert(clientErr instanceof Error ? clientErr.message : "Failed to generate PDF report.");
      }
    } finally {
      setIsDownloading(false);
    }
  }

  async function handleDownloadMarkdown(type: "assessment" | "debt") {
    if (!activeRepo) return;
    setIsDownloading(true);
    setDownloadSuccess("");
    try {
      await reportApi.downloadReport(activeRepo.id, type, "markdown");
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

  async function handleDownloadPptx(type: "assessment" | "debt") {
    if (!activeRepo) return;
    setIsDownloading(true);
    setDownloadSuccess("");
    try {
      await reportApi.downloadReport(activeRepo.id, type, "pptx");
      setDownloadSuccess(
        `PowerPoint Deck '${type === "debt" ? "Technical Debt Plan" : "Quality Assessment"}' downloaded!`
      );
      setTimeout(() => setDownloadSuccess(""), 4000);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to download PowerPoint presentation.");
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
      <Card className="text-center py-16 border border-[#1b273d] bg-[#0d1424] shadow-cyber animate-fade-in">
        <p className="text-sm text-slate-400">Please select an imported repository to view and export reports.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Overview Card with Smooth Scale Lift */}
      <div className="rounded-lg border border-[#1b273d] bg-[#0d1424] p-5 shadow-cyber flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 transition-all duration-300 hover:border-emerald-500/40 hover:shadow-[0_0_20px_rgba(16,185,129,0.15)] hover:scale-[1.008]">
        <div>
          <h2 className="text-base font-bold text-slate-100 tracking-tight">Compiled Code Health Reports</h2>
          <p className="text-xs text-slate-400 mt-1">
            Export authoritative AST security audits and technical debt assessments for{" "}
            <strong className="text-emerald-400 font-mono">{activeRepo.fullName || activeRepo.name}</strong>.
          </p>
        </div>
        {summary && (
          <div className="flex items-center gap-3 text-xs bg-[#070b13] border border-[#1c293e] px-3.5 py-1.5 rounded-md font-mono">
            <span className="font-semibold text-emerald-400">Score: {summary.maintainabilityScore}/100</span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-300">Debt: {summary.technicalDebtHours}h</span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-300">Findings: {summary.findingsCount}</span>
          </div>
        )}
      </div>

      {downloadSuccess && (
        <div className="rounded-md border border-emerald-500/40 bg-emerald-950/40 p-3 text-xs font-semibold text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.2)] animate-fade-in">
          ✓ {downloadSuccess}
        </div>
      )}

      {isLoading ? (
        <Loader message="Loading compiled reports from database..." />
      ) : (
        <div className="space-y-4">
          {/* Report 1: Full Quality & Security Assessment */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between rounded-lg border border-[#1b273d] bg-[#0d1424] p-5 hover:border-emerald-500/50 hover:shadow-[0_0_25px_rgba(16,185,129,0.2)] hover:scale-[1.015] hover:-translate-y-0.5 transition-all duration-300 ease-out gap-4 shadow-cyber group cursor-default">
            <div className="flex items-start gap-3.5">
              <div className="rounded-lg bg-rose-950/60 border border-rose-500/40 p-2.5 text-rose-400 mt-0.5 shadow-[0_0_12px_rgba(244,63,94,0.2)] transition-transform duration-300 group-hover:scale-115">
                <ShieldCheck size={22} />
              </div>
              <div>
                <h3 className="font-bold text-sm text-slate-100">
                  Full Quality and Security Assessment Report
                </h3>
                <p className="text-xs text-slate-400 mt-0.5 font-mono">
                  {activeRepo.fullName || activeRepo.name} | branch: <span className="text-emerald-400">{activeRepo.defaultBranch}</span>
                </p>
                <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
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
                variant="outline"
                size="sm"
                icon={<Download size={14} />}
                onClick={() => handleDownloadPptx("assessment")}
                disabled={!summary}
                isLoading={isDownloading}
              >
                Download PPTX
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
          <div className="flex flex-col sm:flex-row sm:items-center justify-between rounded-lg border border-[#1b273d] bg-[#0d1424] p-5 hover:border-emerald-500/50 hover:shadow-[0_0_25px_rgba(16,185,129,0.2)] hover:scale-[1.015] hover:-translate-y-0.5 transition-all duration-300 ease-out gap-4 shadow-cyber group cursor-default">
            <div className="flex items-start gap-3.5">
              <div className="rounded-lg bg-amber-950/60 border border-amber-500/40 p-2.5 text-amber-400 mt-0.5 shadow-[0_0_12px_rgba(245,158,11,0.2)] transition-transform duration-300 group-hover:scale-115">
                <AlertTriangle size={22} />
              </div>
              <div>
                <h3 className="font-bold text-sm text-slate-100">
                  Technical Debt Analysis and Remediation Plan
                </h3>
                <p className="text-xs text-slate-400 mt-0.5 font-mono">
                  {activeRepo.fullName || activeRepo.name} | branch: <span className="text-emerald-400">{activeRepo.defaultBranch}</span>
                </p>
                <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
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
                variant="outline"
                size="sm"
                icon={<Download size={14} />}
                onClick={() => handleDownloadPptx("debt")}
                disabled={!summary}
                isLoading={isDownloading}
              >
                Download PPTX
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
