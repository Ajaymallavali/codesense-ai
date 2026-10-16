import React, { FormEvent, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  GitBranch,
  MessageSquare,
  RefreshCw,
  Send,
  Sparkles,
} from "lucide-react";
import { Analysis, ChatMessage, Finding, PrReviewData, Repository } from "../types";
import { aiApi } from "../services/aiApi";
import { Button } from "../components/Button";
import { Card } from "../components/Card";

interface AnalysisPageProps {
  activeRepo: Repository | null;
  latestAnalysis: Analysis | null;
  findingsList: Finding[];
  initialFindingFile?: string | null;
  initialFindingId?: string | null;
}

export function AnalysisPage({
  activeRepo,
  latestAnalysis,
  findingsList,
}: AnalysisPageProps) {
  // PR Review State
  const [prReviewData, setPrReviewData] = useState<PrReviewData | null>(null);
  const [isLoadingPrReview, setIsLoadingPrReview] = useState(false);
  const [prReviewError, setPrReviewError] = useState("");
  const [showPrReviewModal, setShowPrReviewModal] = useState(false);
  const [prReviewBranch, setPrReviewBranch] = useState("main");
  const [prReviewTitle, setPrReviewTitle] = useState("");
  const [prReviewDiff, setPrReviewDiff] = useState("");

  // Chat State
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text: `Hello! I am your CodeSense Gemini AI assistant. I have audited your repository's AST structure and findings.\n\nAsk me any questions regarding code security, maintainability refactoring, or launch an Automated PR Review!`,
    },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [isSendingChat, setIsSendingChat] = useState(false);

  // Trigger PR Review
  async function handleTriggerPrReview(e?: FormEvent) {
    if (e) e.preventDefault();
    if (!activeRepo) return;

    setIsLoadingPrReview(true);
    setPrReviewError("");
    try {
      const data = await aiApi.reviewPr({
        repositoryId: activeRepo.id,
        branch: prReviewBranch.trim() || activeRepo.defaultBranch || "main",
        prTitle: prReviewTitle.trim() || `PR Review for ${activeRepo.name}`,
        diff: prReviewDiff.trim() || undefined,
      });
      setPrReviewData(data);
      setShowPrReviewModal(false);
    } catch (err) {
      setPrReviewError(err instanceof Error ? err.message : "Failed to run automated PR review.");
    } finally {
      setIsLoadingPrReview(false);
    }
  }

  // Send Chat message
  async function handleSendChatMessage(e: FormEvent) {
    e.preventDefault();
    const query = chatInput.trim();
    if (!query) return;

    const userMsg: ChatMessage = { role: "user", text: query };
    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    setIsSendingChat(true);

    try {
      const data = await aiApi.chat(activeRepo?.id, query);
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", text: data.response || "No response received from AI engine." },
      ]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Error: Could not reach the Gemini AI review engine. Please check backend connection." },
      ]);
    } finally {
      setIsSendingChat(false);
    }
  }

  // Explain single finding
  async function handleExplainFinding(findingId: string, filePath: string) {
    const userMsg: ChatMessage = { role: "user", text: `Explain issue and suggested remediation for: ${filePath}` };
    setChatMessages((prev) => [...prev, userMsg]);
    setIsSendingChat(true);

    try {
      const data = await aiApi.explain(findingId);
      const reply = `${data.explanation}\n\n${data.suggestion ? `Suggested fix:\n${data.suggestion}` : ""}`;
      setChatMessages((prev) => [...prev, { role: "assistant", text: reply }]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Error: Could not load the explanation from the AI Service." },
      ]);
    } finally {
      setIsSendingChat(false);
    }
  }

  const uniqueFiles = Array.from(new Set(findingsList.map((f) => f.filePath)));

  return (
    <div className="space-y-6">
      {/* Top Banner with Automated PR Review Action */}
      <div className="rounded border border-slate-200 bg-white p-4 sm:p-5 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="rounded bg-teal-50 border border-teal-200 p-2.5 text-teal-800">
            <Sparkles size={22} />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              Gemini AI Review Engine &amp; PR Assistant
              <span className="text-[10px] rounded bg-emerald-50 text-emerald-800 border border-emerald-200 px-2 py-0.5 font-medium">
                AST-Enriched
              </span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Active Repository: <span className="font-semibold text-slate-800">{activeRepo?.fullName || activeRepo?.name || "None"}</span>
              {latestAnalysis && (
                <span className="ml-2 text-slate-400">
                  | Maintainability: {latestAnalysis.maintainabilityScore}/100 | Debt: {latestAnalysis.technicalDebtHours}h
                </span>
              )}
            </p>
          </div>
        </div>

        <Button
          variant="primary"
          size="sm"
          icon={<Sparkles size={14} />}
          onClick={() => {
            setPrReviewTitle(`PR Review: ${activeRepo?.name || "feature"}`);
            setPrReviewBranch(activeRepo?.defaultBranch || "main");
            setShowPrReviewModal(true);
          }}
        >
          Run Automated PR Review
        </Button>
      </div>

      {/* PR Review Modal */}
      {showPrReviewModal && (
        <Card className="border-teal-200 bg-teal-50/50 p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-teal-200 pb-3">
            <div className="flex items-center gap-2">
              <Sparkles size={18} className="text-teal-800" />
              <h3 className="font-bold text-sm text-slate-900">Run Automated Pull Request Review</h3>
            </div>
            <button
              onClick={() => setShowPrReviewModal(false)}
              className="text-xs text-slate-400 hover:text-slate-600 font-semibold"
            >
              ✕ Close
            </button>
          </div>

          <p className="text-xs text-slate-600 leading-relaxed">
            CodeSense cross-references repository AST findings ({findingsList.length} issues), debt metrics, and your proposed PR diff to generate automated inline comments, code patches, and an approval verdict.
          </p>

          <form onSubmit={handleTriggerPrReview} className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block">
                <span className="block text-xs font-medium text-slate-700 mb-1">PR Title / Subject</span>
                <input
                  type="text"
                  value={prReviewTitle}
                  onChange={(e) => setPrReviewTitle(e.target.value)}
                  placeholder="e.g. Refactor auth service and JWT handling"
                  className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 outline-none"
                />
              </label>
              <label className="block">
                <span className="block text-xs font-medium text-slate-700 mb-1">Target Branch</span>
                <input
                  type="text"
                  value={prReviewBranch}
                  onChange={(e) => setPrReviewBranch(e.target.value)}
                  placeholder="main"
                  className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 outline-none"
                />
              </label>
            </div>

            <label className="block">
              <span className="block text-xs font-medium text-slate-700 mb-1">PR Diff / Patch Snippet (Optional)</span>
              <textarea
                rows={4}
                value={prReviewDiff}
                onChange={(e) => setPrReviewDiff(e.target.value)}
                placeholder="Paste git diff or specific code snippet to review alongside repository AST findings."
                className="w-full font-mono text-xs rounded border border-slate-300 bg-white p-3 focus:border-slate-900 outline-none"
              />
            </label>

            {prReviewError && (
              <div className="flex items-center gap-2 rounded border border-rose-200 bg-rose-50 p-2.5 text-xs text-rose-800">
                <AlertCircle size={15} />
                <span>{prReviewError}</span>
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200">
              <Button type="button" variant="outline" size="sm" onClick={() => setShowPrReviewModal(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="sm" isLoading={isLoadingPrReview}>
                Generate Review
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* PR Review Report Display */}
      {prReviewData && (
        <Card className="overflow-hidden p-0 border-slate-300">
          <div className="bg-slate-900 text-white p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <Sparkles size={18} className="text-teal-400" />
              <div>
                <h3 className="font-bold text-sm">Automated PR Review Report</h3>
                <p className="text-[11px] text-slate-400">Synthesized by Gemini AI Review Engine</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`rounded px-2.5 py-1 text-xs font-bold uppercase tracking-wide border ${
                  prReviewData.verdict === "APPROVE"
                    ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                    : prReviewData.verdict === "REQUEST_CHANGES"
                    ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                    : "bg-amber-500/20 text-amber-300 border-amber-500/40"
                }`}
              >
                Verdict: {prReviewData.verdict.replace("_", " ")}
              </span>
              <span className="rounded bg-white/10 px-2 py-1 text-xs text-slate-200 border border-white/10">
                Risk: <strong className="text-white">{prReviewData.riskLevel}</strong>
              </span>
              <button
                onClick={() => setPrReviewData(null)}
                className="text-xs text-slate-400 hover:text-white px-2 py-1 ml-2"
              >
                ✕ Dismiss
              </button>
            </div>
          </div>

          <div className="p-5 space-y-5">
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Executive Summary</h4>
              <p className="text-xs sm:text-sm text-slate-800 leading-relaxed bg-slate-50 p-3.5 rounded border border-slate-200">
                {prReviewData.summary}
              </p>
            </div>

            {prReviewData.suggestedImprovements && prReviewData.suggestedImprovements.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Recommended Improvements</h4>
                <ul className="space-y-1.5 text-xs text-slate-700">
                  {prReviewData.suggestedImprovements.map((imp, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <CheckCircle2 size={14} className="text-teal-600 mt-0.5 shrink-0" />
                      <span>{imp}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {prReviewData.inlineComments && prReviewData.inlineComments.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  Inline Findings &amp; Suggested Fixes ({prReviewData.inlineComments.length})
                </h4>
                <div className="space-y-3">
                  {prReviewData.inlineComments.map((comment, idx) => (
                    <div key={idx} className="rounded border border-slate-200 bg-white p-3.5 shadow-sm space-y-2">
                      <div className="flex items-center justify-between text-xs flex-wrap gap-2">
                        <span className="font-mono font-semibold text-slate-800">
                          {comment.filePath}
                          {comment.lineNumber ? ` : L${comment.lineNumber}` : ""}
                        </span>
                        <span
                          className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${
                            comment.severity.toLowerCase() === "high" || comment.severity.toLowerCase() === "critical"
                              ? "bg-rose-100 text-rose-800"
                              : comment.severity.toLowerCase() === "medium"
                              ? "bg-amber-100 text-amber-800"
                              : "bg-teal-100 text-teal-800"
                          }`}
                        >
                          {comment.severity}
                        </span>
                      </div>
                      <p className="text-xs text-slate-700 leading-relaxed">{comment.comment}</p>
                      {comment.suggestedPatch && (
                        <div className="mt-2 rounded bg-slate-900 p-3 text-slate-100 font-mono text-[11px] overflow-x-auto">
                          <div className="text-[10px] uppercase tracking-wide text-slate-400 mb-1 font-sans">
                            Suggested Code Patch:
                          </div>
                          <pre className="whitespace-pre-wrap">{comment.suggestedPatch}</pre>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Main Split: File Explorer + Gemini Chat */}
      <div className="grid gap-6 lg:grid-cols-[300px_1fr] min-h-[480px]">
        {/* Repository Files List */}
        <Card className="flex flex-col justify-between p-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900 mb-1">Scanned Repository Files</h3>
            <p className="text-xs text-slate-400 mb-4">Click a file to ask Gemini for a targeted remediation fix.</p>
            <ul className="space-y-1 text-xs">
              {uniqueFiles.length === 0 ? (
                <li className="text-slate-400 p-3 text-center">No scanned files with findings.</li>
              ) : (
                uniqueFiles.map((file) => {
                  const simpleName = file.split("/").pop();
                  const fileFindings = findingsList.filter((f) => f.filePath === file);
                  return (
                    <li key={file}>
                      <button
                        onClick={() => {
                          const fnd = fileFindings[0];
                          handleExplainFinding(fnd.id, file);
                        }}
                        className="w-full text-left rounded p-2 hover:bg-slate-50 text-slate-700 hover:text-slate-950 font-medium border border-transparent hover:border-slate-200 transition text-[11px] truncate flex justify-between items-center"
                        title={file}
                      >
                        <span className="truncate">{simpleName}</span>
                        <span className="ml-2 rounded-full bg-rose-50 border border-rose-200 px-1.5 py-0.2 text-[9px] text-rose-800 shrink-0 font-semibold">
                          {fileFindings.length}
                        </span>
                      </button>
                    </li>
                  );
                })
              )}
            </ul>
          </div>
          <div className="border-t border-slate-200 pt-3 text-[11px] text-slate-500">
            AST scan findings loaded dynamically.
          </div>
        </Card>

        {/* Gemini Reviewer Chat */}
        <div className="rounded border border-slate-200 bg-white shadow-sm flex flex-col justify-between overflow-hidden">
          <div className="bg-slate-900 text-white p-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare size={18} />
              <p className="font-bold text-sm">CodeSense Reviewer</p>
            </div>
            <span className="text-[10px] rounded bg-emerald-500/20 text-emerald-300 font-medium px-2 py-0.5 border border-emerald-500/30">
              Gemini AI Review Engine
            </span>
          </div>

          <div className="p-4 space-y-4 flex-1 h-[380px] overflow-y-auto bg-slate-50">
            {chatMessages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-xl rounded p-3 text-xs leading-relaxed ${
                    msg.role === "user"
                      ? "bg-slate-900 text-white rounded-br-none"
                      : "bg-white border border-slate-200 text-slate-700 rounded-bl-none shadow-sm"
                  }`}
                >
                  <p className="whitespace-pre-line">{msg.text}</p>
                </div>
              </div>
            ))}
          </div>

          <form onSubmit={handleSendChatMessage} className="border-t border-slate-200 p-3 bg-white flex gap-2">
            <input
              type="text"
              placeholder="Type code review query or ask about AST findings..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              disabled={isSendingChat}
              className="w-full text-xs rounded border border-slate-300 px-3 py-2 focus:border-slate-900 outline-none"
            />
            <Button type="submit" variant="primary" size="sm" isLoading={isSendingChat} icon={<Send size={14} />}>
              Send
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
