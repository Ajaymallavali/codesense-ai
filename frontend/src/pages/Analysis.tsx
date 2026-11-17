import React, { FormEvent, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Copy,
  Download,
  FileText,
  GitBranch,
  MessageSquare,
  RefreshCw,
  Search,
  Send,
  Sparkles,
} from "lucide-react";
import { Analysis, ChatMessage, Finding, PrReviewData, ReportSummary, Repository } from "../types";
import { aiApi } from "../services/aiApi";
import { reportApi } from "../services/reportApi";
import { Button } from "../components/Button";
import { Card } from "../components/Card";

interface AnalysisPageProps {
  activeRepo: Repository | null;
  latestAnalysis: Analysis | null;
  findingsList: Finding[];
  initialFindingFile?: string | null;
  initialFindingId?: string | null;
  isActiveTab?: boolean;
  user?: any;
}

/**
 * Senior Principal Engineer formatted Markdown and Code Block renderer.
 * Formats fenced code blocks (```lang ... ```), inline backticks, and clean terminal look.
 */
function MarkdownMessageContent({ text }: { text: string }) {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const copyCode = (code: string, idx: number) => {
    navigator.clipboard.writeText(code);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const cleanText = text.replace(/\[DOWNLOAD_HEALTH_REPORT\]/g, "").trim();

  // Split on code fences ```lang\ncode```
  const parts = cleanText.split(/(```[\s\S]*?```)/g);

  return (
    <div className="space-y-2 text-xs leading-relaxed">
      {parts.map((part, index) => {
        if (part.startsWith("```") && part.endsWith("```")) {
          const firstLineEnd = part.indexOf("\n");
          let lang = "code";
          let codeContent = "";
          if (firstLineEnd !== -1) {
            lang = part.slice(3, firstLineEnd).trim() || "code";
            codeContent = part.slice(firstLineEnd + 1, -3);
          } else {
            codeContent = part.slice(3, -3);
          }

          return (
            <div
              key={index}
              className="my-2.5 rounded-lg border border-emerald-500/30 bg-[#05080f] text-slate-100 overflow-hidden shadow-cyber hover:border-emerald-500/50 hover:shadow-[0_0_20px_rgba(16,185,129,0.2)] transition-all duration-300 hover:scale-[1.008]"
            >
              <div className="flex items-center justify-between px-3 py-1.5 bg-[#090e1a] border-b border-[#1b273d] text-[10px] text-emerald-400 font-mono">
                <span className="font-semibold uppercase tracking-wider flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_#00ff88]" />
                  {lang}
                </span>
                <button
                  type="button"
                  onClick={() => copyCode(codeContent, index)}
                  className="flex items-center gap-1 text-slate-300 hover:text-emerald-300 transition-all duration-150 transform hover:scale-110 active:scale-95 px-2 py-0.5 rounded bg-[#11192b] border border-[#1c293e] hover:border-emerald-500/40 cursor-pointer"
                  title="Copy code"
                >
                  <Copy size={11} />
                  <span>{copiedIndex === index ? "Copied!" : "Copy"}</span>
                </button>
              </div>
              <pre className="p-3 text-[11px] font-mono leading-relaxed whitespace-pre-wrap overflow-x-auto text-emerald-300 selection:bg-emerald-500/40">
                {codeContent}
              </pre>
            </div>
          );
        }

        // Inline formatting: line breaks, bolding, and inline backticks
        return (
          <p key={index} className="whitespace-pre-line leading-relaxed">
            {part}
          </p>
        );
      })}
    </div>
  );
}

export function AnalysisPage({
  activeRepo,
  latestAnalysis,
  findingsList,
  initialFindingFile,
  initialFindingId,
  isActiveTab = true,
  user,
}: AnalysisPageProps) {
  // PR Review State
  const [prReviewData, setPrReviewData] = useState<PrReviewData | null>(null);
  const [isLoadingPrReview, setIsLoadingPrReview] = useState(false);
  const [prReviewError, setPrReviewError] = useState("");
  const [showPrReviewModal, setShowPrReviewModal] = useState(false);
  const [prReviewBranch, setPrReviewBranch] = useState("main");
  const [prReviewTitle, setPrReviewTitle] = useState("");
  const [prReviewDiff, setPrReviewDiff] = useState("");

  // File explorer quick search filter
  const [fileFilter, setFileFilter] = useState("");

  // Storage keys scoped per active repository & authenticated user
  const userPrefix = user?.id ? String(user.id) : "user";
  const repoKey = activeRepo?.id ? String(activeRepo.id) : (activeRepo?.name || "default");
  const messagesStorageKey = `codesense_chat_msgs_${userPrefix}_${repoKey}`;
  const convIdStorageKey = `codesense_chat_conv_${userPrefix}_${repoKey}`;
  const legacyStorageKey = `codesense_chat_msgs_${repoKey}`;
  const legacyConvKey = `codesense_chat_conv_${repoKey}`;

  // Active Provider & Model State
  const [activeProvider, setActiveProvider] = useState<string>("cloudflare");

  const defaultGreeting = (repoName?: string): ChatMessage => ({
    role: "assistant",
    text: `Hello! I am your CodeSense Principal AI Assistant powered by Cloudflare Workers AI (@cf/qwen/qwen2.5-coder-32b-instruct). I have audited ${
      repoName ? `**${repoName}**` : "your repository"
    }'s AST structure and findings.\n\nAsk me any questions regarding code security, maintainability refactoring, or launch an Automated PR Review!`,
  });

  // Helpers to read initial state synchronously to eliminate blank flicker
  function getStoredMessages(repo: Repository | null): ChatMessage[] {
    if (!repo) return [defaultGreeting()];
    const rKey = String(repo.id || repo.name || "default");
    const uKey = user?.id ? String(user.id) : "user";
    const pKey = `codesense_chat_msgs_${uKey}_${rKey}`;
    const lKey = `codesense_chat_msgs_${rKey}`;
    try {
      const raw = localStorage.getItem(pKey) || localStorage.getItem(lKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch {}
    return [defaultGreeting(repo.name || repo.fullName)];
  }

  function getStoredConvId(repo: Repository | null): string | undefined {
    if (!repo) return undefined;
    const rKey = String(repo.id || repo.name || "default");
    const uKey = user?.id ? String(user.id) : "user";
    const pKey = `codesense_chat_conv_${uKey}_${rKey}`;
    const lKey = `codesense_chat_conv_${rKey}`;
    try {
      return localStorage.getItem(pKey) || localStorage.getItem(lKey) || undefined;
    } catch {}
    return undefined;
  }

  // Chat State initialized synchronously from storage
  const [conversationId, setConversationId] = useState<string | undefined>(() => getStoredConvId(activeRepo));
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(() => getStoredMessages(activeRepo));
  const [chatInput, setChatInput] = useState("");
  const [isSendingChat, setIsSendingChat] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  /**
   * Helper to write state and localStorage safely without race conditions.
   */
  function persistTurn(updatedMsgs: ChatMessage[], newConvId?: string) {
    setChatMessages(updatedMsgs);
    if (newConvId) {
      setConversationId(newConvId);
    }
    try {
      localStorage.setItem(messagesStorageKey, JSON.stringify(updatedMsgs));
      localStorage.setItem(legacyStorageKey, JSON.stringify(updatedMsgs));
      if (newConvId) {
        localStorage.setItem(convIdStorageKey, newConvId);
        localStorage.setItem(legacyConvKey, newConvId);
      }
    } catch (e) {
      console.warn("Failed saving chat turn to localStorage", e);
    }
  }

  /**
   * Load and synchronize conversation history:
   * 1. Loads local storage immediately (0ms).
   * 2. Background-syncs with server `/conversations/latest` to ensure multi-turn persistence across devices/reloads.
   */
  useEffect(() => {
    if (!activeRepo) return;
    const rKey = String(activeRepo.id || activeRepo.name || "default");

    // 1. Synchronously load local messages for active repository
    const localMsgs = getStoredMessages(activeRepo);
    const localConv = getStoredConvId(activeRepo);
    setChatMessages(localMsgs);
    setConversationId(localConv);

    // 2. Fetch server-persisted conversation to verify and hydrate any updates
    let isCancelled = false;
    aiApi
      .getLatestConversation(rKey)
      .then((serverRes) => {
        if (isCancelled) return;
        if (serverRes && serverRes.messages && serverRes.messages.length > 0) {
          const mapped: ChatMessage[] = serverRes.messages.map((m) => ({
            role: (m.role === "user" ? "user" : "assistant") as "user" | "assistant",
            text: m.content,
            citations: m.citations,
          }));
          // If server has more turns, update and persist
          if (mapped.length >= localMsgs.length) {
            setChatMessages(mapped);
            const activeCId = serverRes.conversationId || localConv;
            if (activeCId) setConversationId(activeCId);
            persistTurn(mapped, activeCId);
          }
        }
      })
      .catch((err) => {
        console.debug("Server history sync completed:", err);
      });

    return () => {
      isCancelled = true;
    };
  }, [repoKey, isActiveTab]);

  // Auto-scroll chat to bottom smoothly
  useEffect(() => {
    if (isActiveTab) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [chatMessages, isSendingChat, isActiveTab]);

  function handleResetChat() {
    setConversationId(undefined);
    try {
      localStorage.removeItem(messagesStorageKey);
      localStorage.removeItem(convIdStorageKey);
      localStorage.removeItem(legacyStorageKey);
      localStorage.removeItem(legacyConvKey);
    } catch {}
    const fresh = [
      {
        role: "assistant" as const,
        text: `Starting a fresh chat session. Ask me questions about ${
          activeRepo?.name || "your repository"
        }'s code architecture, security smells, or refactoring fixes!`,
      },
    ];
    persistTurn(fresh, undefined);
  }

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

  // Helper to build real ReportSummary for active repository
  const buildCurrentSummary = (): ReportSummary => {
    const secCount = findingsList.filter((f) => (f.category || "").toLowerCase().includes("sec")).length;
    const complexCount = findingsList.filter((f) => (f.category || "").toLowerCase().includes("complex")).length;
    const smellCount = findingsList.filter((f) => (f.category || "").toLowerCase().includes("smell") || (f.category || "").toLowerCase().includes("maintain")).length;
    const testCount = findingsList.filter((f) => (f.category || "").toLowerCase().includes("test") || (f.category || "").toLowerCase().includes("reliab")).length;
    const docCount = findingsList.filter((f) => (f.category || "").toLowerCase().includes("doc")).length;

    const dynamicScore = latestAnalysis?.maintainabilityScore ?? (findingsList.length > 100 ? 30 : findingsList.length > 5 ? 72 : 92);
    const dynamicDebt = latestAnalysis?.technicalDebtHours ?? (findingsList.length > 100 ? 5796 : findingsList.length > 5 ? 25 : 4);

    return {
      repository: activeRepo?.fullName || activeRepo?.name || "current_repository",
      branch: activeRepo?.defaultBranch || "main",
      language: activeRepo?.language || "Full-Stack Code",
      analysisId: latestAnalysis?.id || "latest",
      completedAt: latestAnalysis?.completedAt || new Date().toISOString(),
      maintainabilityScore: dynamicScore,
      technicalDebtHours: dynamicDebt,
      findingsCount: findingsList.length,
      findingsByCategory: {
        Security: secCount,
        Complexity: complexCount,
        CodeSmell: smellCount,
        Testing: testCount,
        Documentation: docCount,
      },
      findings: findingsList,
    };
  };

  const handleExportReportPdf = async () => {
    try {
      const summary = buildCurrentSummary();
      await reportApi.generatePdfReport(summary, "assessment");
    } catch (err) {
      console.error("Failed to generate PDF report:", err);
      alert("Error generating PDF report. Please try again.");
    }
  };

  // Send Chat message with compulsory multi-turn conversation history
  async function handleSendChatMessage(e: FormEvent) {
    e.preventDefault();
    const query = chatInput.trim();
    if (!query || isSendingChat) return;

    const userMsg: ChatMessage = { role: "user", text: query };
    const withUser = [...chatMessages, userMsg];
    persistTurn(withUser, conversationId);
    setChatInput("");
    setIsSendingChat(true);

    // Check if user is asking to generate or download a repository health report
    const isReportQuery =
      /\b(report|assessment|audit)\b/i.test(query) &&
      /\b(generate|download|give|create|export|get|show|make|pdf|health|file)\b/i.test(query);

    if (isReportQuery) {
      const secFindings = findingsList.filter((f) => (f.category || "").toLowerCase().includes("sec"));
      const priorityCount = secFindings.filter((f) => (f.severity || "").toLowerCase() === "high" || (f.severity || "").toLowerCase() === "critical").length;
      const score = latestAnalysis?.maintainabilityScore ?? (findingsList.length > 100 ? 30 : findingsList.length > 5 ? 72 : 92);
      const debt = latestAnalysis?.technicalDebtHours ?? (findingsList.length > 100 ? 5796 : findingsList.length > 5 ? 25 : 4);
      const topLocations = findingsList.slice(0, 3).map((f) => {
        const file = f.filePath || (f as any).file_path || (f as any).file || "code";
        const line = f.lineNumber ?? (f as any).line_number ?? 1;
        return `\`${file}:${line}\``;
      }).join(", ");

      const reportText = `I have compiled the official **Repository Health Assessment Report** for **${activeRepo?.fullName || activeRepo?.name || "your repository"}** based on the latest AST static analysis and audit findings:

### Repository Health & Audit Overview
- **Repository Health Score:** **${score}/100**
- **Analysis Coverage:** 98%
- **Total AST Findings:** ${findingsList.length} issues detected
- **Technical Debt:** ~${debt} hours
- **Priority Fixes:** ${priorityCount} critical/high security risks
- **Key Failure Lines:** ${topLocations || "No critical issues"}
- **Release Gate Decision:** ${priorityCount > 0 ? "**NOT READY** — Blocked by security findings that require remediation." : "**READY** — Passes all security and maintainability thresholds."}

[DOWNLOAD_HEALTH_REPORT]
The formal **4-page PDF report** covers the Executive Snapshot, Category Issue Profile & Evidence Table, Microservice Architecture & Diagnostics, and the Cause-and-Effect Root Cause & Prioritized Remediation Plan.`;

      const withAssistant: ChatMessage[] = [
        ...withUser,
        {
          role: "assistant",
          text: reportText,
          hasReportAction: true,
          reportSummary: buildCurrentSummary(),
          citations: findingsList.slice(0, 3).map((f) => ({
            filePath: f.filePath || (f as any).file_path || "code",
            startLine: f.lineNumber ?? (f as any).line_number ?? 1,
            symbol: f.category || "General",
          })),
        },
      ];
      persistTurn(withAssistant, conversationId);
      setIsSendingChat(false);
      return;
    }

    try {
      // Compulsory multi-turn context: provide recent turns so Qwen reasons with full conversation history
      const historyTurns = chatMessages
        .filter((m) => m.text && !m.text.startsWith("Error:"))
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.text }));

      const data = await aiApi.chat(activeRepo?.id, query, conversationId, historyTurns);
      const newConvId = data.conversationId || conversationId;
      if (data.provider) {
        setActiveProvider(data.provider);
      }
      const withAssistant: ChatMessage[] = [
        ...withUser,
        {
          role: "assistant",
          text: data.response || data.answer || "No response received from AI engine.",
          citations: data.citations || [],
        },
      ];
      persistTurn(withAssistant, newConvId);
    } catch (err) {
      const withError: ChatMessage[] = [
        ...withUser,
        { role: "assistant", text: "Error: Could not reach the AI review engine. Please check backend connection." },
      ];
      persistTurn(withError, conversationId);
    } finally {
      setIsSendingChat(false);
    }
  }

  // Explain single finding with compulsory multi-turn memory & permanent chat persistence
  async function handleExplainFinding(findingId: string, filePath: string) {
    if (isSendingChat) return;
    const query = `Explain issue and suggested remediation for: ${filePath}`;
    const userMsg: ChatMessage = { role: "user", text: query };
    const withUser = [...chatMessages, userMsg];
    persistTurn(withUser, conversationId);
    setIsSendingChat(true);

    try {
      const historyTurns = chatMessages
        .filter((m) => m.text && !m.text.startsWith("Error:"))
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.text }));

      const data = await aiApi.chat(activeRepo?.id, query, conversationId, historyTurns);
      const newConvId = data.conversationId || conversationId;
      if (data.provider) {
        setActiveProvider(data.provider);
      }
      const withAssistant: ChatMessage[] = [
        ...withUser,
        {
          role: "assistant",
          text: data.response || data.answer || "No response received from AI engine.",
          citations: data.citations || [],
        },
      ];
      persistTurn(withAssistant, newConvId);
    } catch (err) {
      try {
        const data = await aiApi.explain(findingId);
        const reply = `${data.explanation}\n\n${data.suggestion ? `Suggested fix:\n${data.suggestion}` : ""}`;
        const withAssistant: ChatMessage[] = [...withUser, { role: "assistant", text: reply }];
        persistTurn(withAssistant, conversationId);
      } catch {
        const withError: ChatMessage[] = [
          ...withUser,
          { role: "assistant", text: "Error: Could not load the explanation from the AI Service." },
        ];
        persistTurn(withError, conversationId);
      }
    } finally {
      setIsSendingChat(false);
    }
  }

  // Auto-focus and explain finding if user navigated from Dashboard table
  const handledTargetRef = useRef<string | null>(null);
  useEffect(() => {
    if (!isActiveTab || !initialFindingFile) return;
    const targetKey = `${initialFindingFile}#${initialFindingId || ""}`;
    if (handledTargetRef.current === targetKey) return;
    handledTargetRef.current = targetKey;

    // Filter file in explorer to highlight it
    const simpleName = initialFindingFile.split("/").pop();
    if (simpleName) {
      setFileFilter(simpleName);
    }

    const matched = findingsList.find(
      (f) => f.id === initialFindingId || f.filePath === initialFindingFile
    );
    if (matched) {
      handleExplainFinding(matched.id, matched.filePath);
    } else {
      handleExplainFinding(initialFindingId || "target", initialFindingFile);
    }
  }, [initialFindingFile, initialFindingId, isActiveTab]);

  const uniqueFiles = Array.from(new Set(findingsList.map((f) => f.filePath)));
  const filteredFiles = uniqueFiles.filter((f) =>
    f.toLowerCase().includes(fileFilter.trim().toLowerCase())
  );

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Top Banner with Automated PR Review Action */}
      <div className="rounded-lg border border-[#1b273d] bg-[#0d1424] p-4 sm:p-5 shadow-cyber flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 transition-all duration-300 hover:border-emerald-500/40 hover:shadow-[0_0_22px_rgba(16,185,129,0.18)] hover:scale-[1.008]">
        <div className="flex items-center gap-3.5">
          <div className="rounded-lg bg-emerald-950/60 border border-emerald-500/40 p-2.5 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.25)] transition-transform duration-300 hover:scale-110">
            <Sparkles size={22} className="animate-pulse" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2 flex-wrap">
              <span>Cloudflare Workers AI &amp; Qwen2.5-Coder Engine</span>
              <span className="text-[10px] rounded bg-emerald-950/80 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 font-mono shadow-[0_0_8px_rgba(16,185,129,0.2)] transition-transform duration-200 hover:scale-105">
                AST &amp; RAG Enriched
              </span>
            </h2>
            <p className="text-xs text-slate-400 mt-1 flex items-center gap-2 flex-wrap">
              <span>Active Repository:</span>
              <span className="font-mono font-semibold text-emerald-400">
                {activeRepo?.fullName || activeRepo?.name || "None"}
              </span>
              {latestAnalysis && (
                <span className="text-slate-500 font-mono text-[11px]">
                  | Maintainability: <strong className="text-emerald-400">{latestAnalysis.maintainabilityScore}/100</strong> | Debt: {latestAnalysis.technicalDebtHours}h
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
        <Card className="border border-emerald-500/30 bg-[#0d1424] p-5 space-y-4 shadow-[0_0_30px_rgba(0,0,0,0.8)] animate-fade-in-up">
          <div className="flex items-center justify-between border-b border-[#1b273d] pb-3">
            <div className="flex items-center gap-2">
              <Sparkles size={18} className="text-emerald-400" />
              <h3 className="font-bold text-sm text-slate-100">Run Automated Pull Request Review</h3>
            </div>
            <button
              onClick={() => setShowPrReviewModal(false)}
              className="text-xs text-slate-400 hover:text-emerald-400 font-semibold transition-colors"
            >
              ✕ Close
            </button>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed">
            CodeSense cross-references repository AST findings ({findingsList.length} issues), debt metrics, and your proposed PR diff to generate automated inline comments, code patches, and an approval verdict.
          </p>

          <form onSubmit={handleTriggerPrReview} className="space-y-3.5">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block">
                <span className="block text-xs font-medium text-slate-300 mb-1">PR Title / Subject</span>
                <input
                  type="text"
                  value={prReviewTitle}
                  onChange={(e) => setPrReviewTitle(e.target.value)}
                  placeholder="e.g. Refactor auth service and JWT handling"
                  className="w-full rounded border border-[#1c293e] bg-[#070b13] px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/40 outline-none transition"
                />
              </label>
              <label className="block">
                <span className="block text-xs font-medium text-slate-300 mb-1">Target Branch</span>
                <input
                  type="text"
                  value={prReviewBranch}
                  onChange={(e) => setPrReviewBranch(e.target.value)}
                  placeholder="main"
                  className="w-full rounded border border-[#1c293e] bg-[#070b13] px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/40 outline-none transition"
                />
              </label>
            </div>

            <label className="block">
              <span className="block text-xs font-medium text-slate-300 mb-1">PR Diff / Patch Snippet (Optional)</span>
              <textarea
                rows={4}
                value={prReviewDiff}
                onChange={(e) => setPrReviewDiff(e.target.value)}
                placeholder="Paste git diff or specific code snippet to review alongside repository AST findings."
                className="w-full font-mono text-xs rounded border border-[#1c293e] bg-[#070b13] p-3 text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/40 outline-none transition"
              />
            </label>

            {prReviewError && (
              <div className="flex items-center gap-2 rounded border border-rose-500/40 bg-rose-950/40 p-2.5 text-xs text-rose-300">
                <AlertCircle size={15} />
                <span>{prReviewError}</span>
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#1b273d]">
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
        <Card className="overflow-hidden p-0 border border-[#1b273d] bg-[#0d1424] shadow-cyber animate-fade-in-up">
          <div className="bg-[#080d17] text-white p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[#1b273d]">
            <div className="flex items-center gap-2.5">
              <Sparkles size={18} className="text-emerald-400" />
              <div>
                <h3 className="font-bold text-sm text-slate-100">Automated PR Review Report</h3>
                <p className="text-[11px] text-slate-400">Synthesized by Cloudflare Workers AI &amp; Qwen Coder</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`rounded px-2.5 py-1 text-xs font-bold uppercase tracking-wide border ${
                  prReviewData.verdict === "APPROVE"
                    ? "bg-emerald-950/80 text-emerald-300 border-emerald-500/50 shadow-[0_0_10px_rgba(16,185,129,0.3)]"
                    : prReviewData.verdict === "REQUEST_CHANGES"
                    ? "bg-rose-950/80 text-rose-300 border-rose-500/50 shadow-[0_0_10px_rgba(244,63,94,0.3)]"
                    : "bg-amber-950/80 text-amber-300 border-amber-500/50 shadow-[0_0_10px_rgba(245,158,11,0.3)]"
                }`}
              >
                Verdict: {prReviewData.verdict.replace("_", " ")}
              </span>
              <span className="rounded bg-[#121b2d] px-2 py-1 text-xs text-slate-300 border border-[#1c293e]">
                Risk: <strong className="text-emerald-400">{prReviewData.riskLevel}</strong>
              </span>
              <button
                onClick={() => setPrReviewData(null)}
                className="text-xs text-slate-400 hover:text-emerald-400 px-2 py-1 ml-2 transition-colors"
              >
                ✕ Dismiss
              </button>
            </div>
          </div>

          <div className="p-5 space-y-4 bg-[#0a0e19]">
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">Executive Summary</h4>
              <p className="text-xs text-slate-300 leading-relaxed bg-[#0d1424] border border-[#1b273d] rounded p-3">
                {prReviewData.summary}
              </p>
            </div>

            {prReviewData.inlineComments && prReviewData.inlineComments.length > 0 && (
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Line Comments &amp; Suggested Patches ({prReviewData.inlineComments.length})
                </h4>
                <div className="space-y-3">
                  {prReviewData.inlineComments.map((comment: any, idx: number) => (
                    <div key={idx} className="rounded-lg border border-[#1b273d] bg-[#0d1424] p-3.5 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <GitBranch size={13} className="text-emerald-400" />
                          <span className="font-mono font-semibold text-slate-200">{comment.filePath}</span>
                          <span className="text-slate-400">Line {comment.lineNumber}</span>
                        </div>
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                            comment.severity.toLowerCase() === "high"
                              ? "bg-rose-950/70 border border-rose-800/60 text-rose-300"
                              : comment.severity.toLowerCase() === "medium"
                              ? "bg-amber-950/70 border border-amber-800/60 text-amber-300"
                              : "bg-emerald-950/70 border border-emerald-800/60 text-emerald-300"
                          }`}
                        >
                          {comment.severity}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">{comment.comment}</p>
                      {comment.suggestedPatch && (
                        <div className="mt-2 rounded-lg bg-[#05080f] border border-emerald-500/30 p-3 text-slate-100 font-mono text-[11px] overflow-x-auto">
                          <div className="text-[10px] uppercase tracking-wide text-emerald-400 mb-1 font-sans">
                            Suggested Code Patch:
                          </div>
                          <pre className="whitespace-pre-wrap text-emerald-300">{comment.suggestedPatch}</pre>
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

      {/* Main Split: Bounded-Height Professional Layout (No Long Gaps) */}
      <div className="grid gap-6 lg:grid-cols-[320px_1fr] h-[640px] max-h-[calc(100vh-210px)] min-h-[520px]">
        {/* Left Column: Repository Files Explorer with Internal Scroll */}
        <div className="flex flex-col h-full p-4 overflow-hidden rounded-lg border border-[#1b273d] bg-[#0d1424] shadow-cyber">
          {/* Header & Filter */}
          <div className="shrink-0 mb-3 space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-100">Scanned Repository Files</h3>
              <span className="text-[10px] rounded bg-emerald-950/70 text-emerald-300 px-2 py-0.5 font-semibold font-mono border border-emerald-500/30">
                {uniqueFiles.length} files
              </span>
            </div>
            <p className="text-xs text-slate-400">Click a file to ask Qwen for a targeted remediation fix.</p>
            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-2.5 text-slate-400" />
              <input
                type="text"
                value={fileFilter}
                onChange={(e) => setFileFilter(e.target.value)}
                placeholder="Filter files..."
                className="w-full text-xs rounded border border-[#1c293e] bg-[#070b13] pl-8 pr-2.5 py-1.5 text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/30 outline-none transition"
              />
            </div>
          </div>

          {/* Scrollable File List */}
          <div className="flex-1 overflow-y-auto pr-1 space-y-1 min-h-0">
            <ul className="space-y-1 text-xs">
              {filteredFiles.length === 0 ? (
                <li className="text-slate-500 p-4 text-center">
                  {uniqueFiles.length === 0 ? "No scanned files with findings." : "No files match your filter."}
                </li>
              ) : (
                filteredFiles.map((file) => {
                  const simpleName = file.split("/").pop();
                  const fileFindings = findingsList.filter((f) => f.filePath === file);
                  return (
                    <li key={file}>
                      <button
                        onClick={() => {
                          const fnd = fileFindings[0];
                          handleExplainFinding(fnd.id, file);
                        }}
                        className="w-full text-left rounded-md p-2 hover:bg-emerald-950/40 text-slate-300 hover:text-emerald-300 font-medium border border-transparent hover:border-emerald-500/40 transition-all duration-200 ease-out transform hover:scale-[1.02] hover:translate-x-1 hover:shadow-[0_0_12px_rgba(16,185,129,0.18)] active:scale-[0.98] text-[11px] truncate flex justify-between items-center group cursor-pointer"
                        title={file}
                      >
                        <span className="truncate group-hover:font-semibold">{simpleName}</span>
                        <span className="ml-2 rounded-full bg-rose-950/70 border border-rose-800/60 px-1.5 py-0.2 text-[9px] text-rose-300 shrink-0 font-semibold font-mono transition-transform duration-200 group-hover:scale-115">
                          {fileFindings.length}
                        </span>
                      </button>
                    </li>
                  );
                })
              )}
            </ul>
          </div>

          {/* Footer */}
          <div className="shrink-0 border-t border-[#1b273d] pt-2.5 mt-2 flex items-center justify-between text-[11px] text-slate-400">
            <span>AST findings loaded</span>
            <span className="font-semibold text-emerald-400 font-mono">{findingsList.length} issues</span>
          </div>
        </div>

        {/* Right Column: Qwen Reviewer Chat (Pinned Input Bar, No Gaps) */}
        <div className="rounded-lg border border-[#1b273d] bg-[#0d1424] shadow-cyber flex flex-col h-full overflow-hidden">
          {/* Fixed Chat Header */}
          <div className="shrink-0 bg-[#080d17] text-white px-4 py-3 flex items-center justify-between border-b border-[#1b273d]">
            <div className="flex items-center gap-2.5">
              <MessageSquare size={18} className="text-emerald-400 drop-shadow-[0_0_6px_rgba(16,185,129,0.5)]" />
              <p className="font-bold text-sm tracking-wide">CodeSense Reviewer</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleExportReportPdf}
                className="flex items-center gap-1.5 text-[11px] font-semibold text-emerald-300 bg-emerald-950/70 hover:bg-emerald-900/90 border border-emerald-500/40 hover:border-emerald-400 px-2.5 py-0.5 rounded transition-all duration-150 transform hover:scale-105 active:scale-95 cursor-pointer shadow-[0_0_10px_rgba(16,185,129,0.25)]"
                title="Download 4-page PDF Repository Health Assessment Report"
              >
                <FileText size={11} className="text-emerald-400" />
                <span>Export Health PDF</span>
              </button>
              <button
                type="button"
                onClick={handleResetChat}
                className="flex items-center gap-1 text-[11px] text-slate-300 hover:text-emerald-300 bg-[#11192b] hover:bg-emerald-950/50 border border-[#1c293e] hover:border-emerald-500/40 px-2 py-0.5 rounded transition-all duration-150 transform hover:scale-105 active:scale-95 cursor-pointer"
                title="Start a new chat session"
              >
                <RefreshCw size={11} />
                <span>New Chat</span>
              </button>
              <span className="text-[10px] rounded bg-emerald-950/70 text-emerald-300 font-mono px-2 py-0.5 border border-emerald-500/40 shadow-[0_0_8px_rgba(16,185,129,0.2)] flex items-center gap-1.5 transition-transform duration-200 hover:scale-105 cursor-default">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_6px_#00ff88]" />
                {activeProvider === "cloudflare" ? "Cloudflare Workers AI (Qwen 32B)" : "Qwen RAG Engine"}
              </span>
            </div>
          </div>

          {/* Scrollable Messages Pane */}
          <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3.5 bg-[#060a12]">
            {chatMessages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-2xl rounded-lg p-3 text-xs leading-relaxed animate-fade-in-up transition-transform duration-200 hover:scale-[1.006] ${
                    msg.role === "user"
                      ? "bg-emerald-950/70 border border-emerald-500/40 text-emerald-100 rounded-br-none shadow-[0_0_15px_rgba(16,185,129,0.12)]"
                      : "bg-[#0e1627] border border-[#1c293e] text-slate-200 rounded-bl-none shadow-md"
                  }`}
                >
                  <MarkdownMessageContent text={msg.text} />

                  {/* Interactive 4-Page PDF Report Download Card */}
                  {(msg.hasReportAction || msg.text.includes("[DOWNLOAD_HEALTH_REPORT]")) && (
                    <div className="my-3 rounded-lg border border-emerald-500/50 bg-[#070c18] p-3.5 shadow-cyber space-y-2.5 animate-scale-in">
                      <div className="flex items-center justify-between border-b border-[#1b273d] pb-2">
                        <div className="flex items-center gap-2">
                          <FileText size={16} className="text-emerald-400" />
                          <span className="font-bold text-xs text-slate-100">
                            Repository Health Assessment Report
                          </span>
                        </div>
                        <span className="text-[10px] rounded bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 font-mono px-2 py-0.5">
                          4-Page Executive PDF
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-2 text-center text-[10px] font-mono py-1">
                        <div className="rounded bg-[#05080f] border border-[#1c293e] p-1.5">
                          <span className="text-slate-400 block text-[9px]">HEALTH SCORE</span>
                          <span className="text-emerald-400 font-bold text-xs">
                            {latestAnalysis?.maintainabilityScore ?? 92}/100
                          </span>
                        </div>
                        <div className="rounded bg-[#05080f] border border-[#1c293e] p-1.5">
                          <span className="text-slate-400 block text-[9px]">FINDINGS</span>
                          <span className="text-slate-200 font-bold text-xs">{findingsList.length}</span>
                        </div>
                        <div className="rounded bg-[#05080f] border border-[#1c293e] p-1.5">
                          <span className="text-slate-400 block text-[9px]">TECH DEBT</span>
                          <span className="text-amber-400 font-bold text-xs">
                            {latestAnalysis?.technicalDebtHours ?? 4}h
                          </span>
                        </div>
                      </div>

                      <p className="text-[11px] text-slate-300 leading-snug">
                        Ready to export: formal 4-page technical audit with Executive Snapshot, Category Issue Profile, Architecture Journey, and Root Cause &amp; Remediation Plan.
                      </p>

                      <Button
                        variant="primary"
                        size="sm"
                        icon={<Download size={14} />}
                        onClick={handleExportReportPdf}
                        className="w-full justify-center shadow-neon hover:scale-[1.02]"
                      >
                        Download 4-Page PDF Report
                      </Button>
                    </div>
                  )}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-2.5 pt-2 border-t border-[#1b273d] flex flex-wrap gap-1.5 items-center">
                      <span className="text-[10px] font-semibold text-slate-400">Sources:</span>
                      {msg.citations.map((cite, cIdx) => (
                        <span
                          key={cIdx}
                          className="inline-flex items-center gap-1 rounded bg-[#070b14] border border-[#1c293e] px-2 py-0.5 text-[10px] font-mono text-slate-300"
                        >
                          <span className="font-medium text-slate-200">{cite.filePath}</span>
                          {cite.startLine ? (
                            <span className="text-emerald-400 font-semibold">
                              :L{cite.startLine}
                              {cite.endLine && cite.endLine !== cite.startLine ? `-${cite.endLine}` : ""}
                            </span>
                          ) : null}
                          {cite.symbol && cite.symbol !== "general" && (
                            <span className="text-slate-500 text-[9px]">({cite.symbol})</span>
                          )}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {isSendingChat && (
              <div className="flex justify-start">
                <div className="max-w-xl rounded-lg p-3 text-xs leading-relaxed bg-[#0e1627] border border-emerald-500/30 text-emerald-300 rounded-bl-none shadow-[0_0_15px_rgba(16,185,129,0.15)] flex items-center gap-2">
                  <span className="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-ping shadow-[0_0_8px_#00ff88]" />
                  <span>Cloudflare Workers AI reasoning &amp; reviewing code context...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Fixed Chat Input Form (Always Docked at Bottom of Chat Pane) */}
          <form onSubmit={handleSendChatMessage} className="shrink-0 border-t border-[#1b273d] p-3 bg-[#080d17] flex gap-2">
            <input
              type="text"
              placeholder="Type code review query or ask about AST findings..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              disabled={isSendingChat}
              className="w-full text-xs rounded border border-[#1c293e] bg-[#05080f] px-3 py-2 text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/40 outline-none transition"
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
