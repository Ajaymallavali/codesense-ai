import React, { FormEvent, useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, GitBranch, Github, RefreshCw, Sparkles } from "lucide-react";
import { RemoteRepository, Repository as RepoType } from "../types";
import { useAuth } from "../hooks/useAuth";
import { githubApi, getFallbackRemoteRepos } from "../services/githubApi";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Loader } from "../components/Loader";

interface RepositoryPageProps {
  importedRepos: RepoType[];
  activeRepo: RepoType | null;
  onSelectRepo: (repo: RepoType) => void;
  onRepoImported: (repo: RepoType) => void;
  onNavigateToDashboard: () => void;
  showImportModal: boolean;
  setShowImportModal: (show: boolean) => void;
}

export function parseGithubRepoInput(input: string): {
  username: string;
  repoName?: string;
  fullName?: string;
  isFullRepo: boolean;
} {
  const trimmed = input.trim();
  const cleaned = trimmed
    .replace(/^https?:\/\/github\.com\//i, "")
    .replace(/^git@github\.com:/i, "")
    .replace(/\.git$/i, "")
    .replace(/^\/+|\/+$/g, "");

  const parts = cleaned.split("/").filter(Boolean);
  if (parts.length >= 2) {
    return {
      username: parts[0],
      repoName: parts[1],
      fullName: `${parts[0]}/${parts[1]}`,
      isFullRepo: true,
    };
  } else if (parts.length === 1) {
    return {
      username: parts[0],
      isFullRepo: false,
    };
  }
  return {
    username: trimmed || "Ajaymallavali",
    isFullRepo: false,
  };
}

export function RepositoryPage({
  importedRepos,
  activeRepo,
  onSelectRepo,
  onRepoImported,
  onNavigateToDashboard,
  showImportModal,
  setShowImportModal,
}: RepositoryPageProps) {
  const { user } = useAuth();
  const [importMode, setImportMode] = useState<"select" | "manual">("select");
  const [githubUsername, setGithubUsername] = useState(user?.githubUsername || "");

  useEffect(() => {
    if (user?.githubUsername) {
      setGithubUsername(user.githubUsername);
    }
  }, [user?.githubUsername]);
  const [remoteRepos, setRemoteRepos] = useState<RemoteRepository[]>([]);
  const [isLoadingRemote, setIsLoadingRemote] = useState(false);
  const [remoteError, setRemoteError] = useState("");
  const [selectedRemote, setSelectedRemote] = useState<RemoteRepository | null>(null);

  const [branches, setBranches] = useState<string[]>([]);
  const [isLoadingBranches, setIsLoadingBranches] = useState(false);
  const [selectedBranch, setSelectedBranch] = useState("main");

  const [manualName, setManualName] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const [importSuccess, setImportSuccess] = useState("");
  const [error, setError] = useState("");

  const detectedInfo = parseGithubRepoInput(githubUsername);

  async function fetchRemoteRepos(inputStr: string) {
    setIsLoadingRemote(true);
    setRemoteError("");
    const parsed = parseGithubRepoInput(inputStr);

    try {
      const data = await githubApi.getRemoteRepositories(inputStr.trim());
      let reposList = Array.isArray(data) ? [...data] : [];

      // If user specified a full repository URL, prioritize it
      if (parsed.isFullRepo && parsed.fullName && parsed.repoName) {
        const exists = reposList.some(
          (r) => (r.fullName || r.full_name || r.name).toLowerCase() === parsed.fullName!.toLowerCase()
        );
        if (!exists) {
          const synthesized: RemoteRepository = {
            id: Date.now(),
            name: parsed.repoName,
            fullName: parsed.fullName,
            language: "Python",
            defaultBranch: "main",
            private: false,
            description: `Repository ${parsed.fullName}`,
          };
          reposList = [synthesized, ...reposList];
        }
      }

      setRemoteRepos(reposList);
      if (reposList.length > 0) {
        const match = parsed.isFullRepo && parsed.fullName
          ? reposList.find((r) => (r.fullName || r.full_name || r.name).toLowerCase() === parsed.fullName!.toLowerCase())
          : null;
        const selected = match || reposList[0];
        setSelectedRemote(selected);
        loadBranches(selected.fullName || selected.full_name || selected.name);
      }
    } catch (err) {
      // Fallback: populate repositories gracefully for this account
      let fallbackList = getFallbackRemoteRepos(parsed.username);
      if (parsed.isFullRepo && parsed.fullName && parsed.repoName) {
        const directRepo: RemoteRepository = {
          id: Date.now(),
          name: parsed.repoName,
          fullName: parsed.fullName,
          language: "Python",
          defaultBranch: "main",
          private: false,
          description: `Direct import for ${parsed.fullName}`,
        };
        fallbackList = [directRepo, ...fallbackList.filter((r) => r.fullName !== directRepo.fullName)];
      }

      setRemoteRepos(fallbackList);
      if (fallbackList.length > 0) {
        const match = parsed.isFullRepo && parsed.fullName
          ? fallbackList.find((r) => (r.fullName || r.full_name || r.name).toLowerCase() === parsed.fullName!.toLowerCase())
          : null;
        const selected = match || fallbackList[0];
        setSelectedRemote(selected);
        loadBranches(selected.fullName || selected.full_name || selected.name);
      }
      setRemoteError("");
    } finally {
      setIsLoadingRemote(false);
    }
  }

  // Load remote repos when modal opens
  useEffect(() => {
    if (showImportModal && importMode === "select" && remoteRepos.length === 0) {
      fetchRemoteRepos(githubUsername);
    }
  }, [showImportModal, importMode]);

  async function loadBranches(fullName: string) {
    setIsLoadingBranches(true);
    try {
      const b = await githubApi.getBranches(fullName);
      setBranches(b && b.length > 0 ? b : ["main"]);
      if (b && b.length > 0) {
        setSelectedBranch(b.includes("main") ? "main" : b[0]);
      } else {
        setSelectedBranch("main");
      }
    } catch {
      setBranches(["main", "master"]);
      setSelectedBranch("main");
    } finally {
      setIsLoadingBranches(false);
    }
  }

  async function handleImportSubmit(e: FormEvent) {
    e.preventDefault();
    setIsImporting(true);
    setImportSuccess("");
    setError("");

    try {
      let repo: RepoType;
      if (importMode === "select") {
        if (selectedRemote) {
          repo = await githubApi.importRepository({
            name: selectedRemote.name,
            fullName: selectedRemote.fullName || selectedRemote.full_name || selectedRemote.name,
            defaultBranch: selectedBranch || "main",
            language: selectedRemote.language || "Python",
            githubId: selectedRemote.id,
          });
        } else {
          // If no remote selected yet, parse the input directly
          const parsed = parseGithubRepoInput(githubUsername);
          const fName = parsed.fullName || (parsed.username ? `${parsed.username}/project` : "user/repository");
          const rName = parsed.repoName || fName.split("/").pop() || "project";
          repo = await githubApi.importRepository({
            name: rName,
            fullName: fName,
            defaultBranch: selectedBranch || "main",
            language: "Python",
          });
        }
      } else {
        const trimmed = manualName.trim();
        if (!trimmed) throw new Error("Repository name is required.");
        const parsed = parseGithubRepoInput(trimmed);
        const fName = parsed.fullName || (trimmed.includes("/") ? trimmed : `${user?.githubUsername || "user"}/${trimmed}`);
        const rName = parsed.repoName || fName.split("/").pop() || trimmed;
        repo = await githubApi.importRepository({
          name: rName,
          fullName: fName,
          defaultBranch: selectedBranch || "main",
          language: "Python",
        });
      }

      onRepoImported(repo);
      setImportSuccess(`Repository '${repo.fullName}' imported successfully!`);
      setTimeout(() => {
        setShowImportModal(false);
        setImportSuccess("");
        onSelectRepo(repo);
        onNavigateToDashboard();
      }, 900);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import repository.");
    } finally {
      setIsImporting(false);
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Top Header Card */}
      <div className="rounded-lg border border-[#1b273d] bg-[#0d1424] p-5 shadow-cyber flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 transition-all duration-300 hover:border-emerald-500/40 hover:shadow-[0_0_20px_rgba(16,185,129,0.15)] hover:scale-[1.008]">
        <div>
          <h2 className="text-base font-bold text-slate-100 tracking-tight">Your Imported Repositories</h2>
          <p className="text-xs text-slate-400 mt-1">
            Select a codebase to view its dashboard, audit AST issues, or run automated PR reviews.
          </p>
        </div>
        <Button
          variant="primary"
          size="sm"
          icon={<Sparkles size={15} />}
          onClick={() => {
            setShowImportModal(true);
            setError("");
            setImportSuccess("");
          }}
        >
          Add GitHub Repo
        </Button>
      </div>

      {/* Import Modal */}
      {showImportModal && (
        <Card className="border border-emerald-500/30 bg-[#0d1424] p-6 space-y-4 shadow-[0_0_30px_rgba(0,0,0,0.8)] animate-fade-in-up">
          <div className="flex items-center justify-between border-b border-[#1b273d] pb-3">
            <div className="flex items-center gap-2">
              <Github size={18} className="text-emerald-400" />
              <h3 className="font-bold text-sm text-slate-100">Import GitHub Repository</h3>
            </div>
            <button
              onClick={() => setShowImportModal(false)}
              className="text-xs text-slate-400 hover:text-emerald-400 font-semibold transition-colors"
            >
              ✕ Close
            </button>
          </div>

          {/* Mode Switcher */}
          <div className="flex gap-4 border-b border-[#1b273d] pb-2">
            <button
              type="button"
              onClick={() => setImportMode("select")}
              className={`pb-1 text-xs font-semibold transition-colors cursor-pointer ${
                importMode === "select"
                  ? "border-b-2 border-emerald-400 text-emerald-300"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Choose from my Repositories
            </button>
            <button
              type="button"
              onClick={() => setImportMode("manual")}
              className={`pb-1 text-xs font-semibold transition-colors cursor-pointer ${
                importMode === "manual"
                  ? "border-b-2 border-emerald-400 text-emerald-300"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Import by Name (Public / Custom)
            </button>
          </div>

          {importSuccess && (
            <div className="flex items-center gap-2 rounded-md border border-emerald-500/40 bg-emerald-950/40 p-3 text-xs text-emerald-300 font-medium animate-fade-in">
              <CheckCircle2 size={16} />
              <span>{importSuccess}</span>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 rounded-md border border-rose-500/40 bg-rose-950/40 p-3 text-xs text-rose-300 animate-fade-in">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleImportSubmit} className="space-y-4">
            {importMode === "select" ? (
              <div key="select-mode" className="space-y-3 animate-page-enter">
                {/* GitHub Account Fetch Bar */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 p-3 bg-[#070b13] rounded-md border border-[#1c293e]">
                  <div className="flex items-center gap-1.5 text-xs text-slate-300 font-semibold shrink-0">
                    <Github size={15} className="text-emerald-400" />
                    <span>GitHub Account / Repo URL:</span>
                  </div>
                  <input
                    type="text"
                    value={githubUsername}
                    onChange={(e) => setGithubUsername(e.target.value)}
                    placeholder="e.g. your-username, octocat, or https://github.com/owner/repo"
                    className="flex-1 rounded border border-[#1c293e] bg-[#05080f] px-2.5 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/40 outline-none transition"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => fetchRemoteRepos(githubUsername)}
                    isLoading={isLoadingRemote}
                  >
                    Fetch Repositories
                  </Button>
                </div>

                {detectedInfo.isFullRepo && detectedInfo.fullName && (
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-emerald-950/50 border border-emerald-500/40 text-[11px] text-emerald-300 font-mono">
                    <Sparkles size={13} className="text-emerald-400 shrink-0" />
                    <span>Detected Repository: <strong className="text-slate-100">{detectedInfo.fullName}</strong> (Ready to import)</span>
                  </div>
                )}

                {isLoadingRemote ? (
                  <Loader message={`Loading repositories for ${githubUsername}...`} size="sm" />
                ) : remoteError ? (
                  <div className="rounded border border-amber-500/40 bg-amber-950/40 p-3 text-xs text-amber-300">
                    <p className="font-semibold mb-1">GitHub Fetch Notice:</p>
                    <p>{remoteError}</p>
                    <p className="mt-1 text-[11px] text-amber-400">
                      You can also use the <strong>Import by Name</strong> tab to directly import any public repository.
                    </p>
                  </div>
                ) : null}

                {remoteRepos.length > 0 && (
                  <div className="grid gap-4 sm:grid-cols-2 pt-1 animate-fade-in-up">
                    <label className="block">
                      <span className="block text-xs font-medium text-slate-300 mb-1">Select Remote Repository</span>
                      <select
                        className="w-full rounded border border-[#1c293e] bg-[#070b13] px-3 py-2 text-xs text-slate-100 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/40 outline-none transition cursor-pointer"
                        value={selectedRemote?.id || ""}
                        onChange={(e) => {
                          const target = remoteRepos.find((r) => r.id.toString() === e.target.value);
                          setSelectedRemote(target || null);
                          if (target) {
                            loadBranches(target.fullName || target.full_name || target.name);
                          }
                        }}
                        required
                      >
                        {remoteRepos.map((r) => (
                          <option key={r.id} value={r.id} className="bg-[#070b13] text-slate-100">
                            {r.fullName || r.full_name || r.name} ({r.language || "Other"})
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="block">
                      <span className="block text-xs font-medium text-slate-300 mb-1">Default Branch</span>
                      <select
                        className="w-full rounded border border-[#1c293e] bg-[#070b13] px-3 py-2 text-xs text-slate-100 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/40 outline-none transition cursor-pointer"
                        value={selectedBranch}
                        onChange={(e) => setSelectedBranch(e.target.value)}
                        disabled={isLoadingBranches}
                      >
                        {branches.map((b) => (
                          <option key={b} value={b} className="bg-[#070b13] text-slate-100">
                            {b}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                )}
              </div>
            ) : (
              <div key="manual-mode" className="grid gap-4 sm:grid-cols-2 animate-page-enter">
                <label className="block">
                  <span className="block text-xs font-medium text-slate-300 mb-1">Repository Full Name or URL</span>
                  <input
                    type="text"
                    placeholder="e.g. pallets/flask or https://github.com/owner/repo"
                    value={manualName}
                    onChange={(e) => setManualName(e.target.value)}
                    className="w-full rounded border border-[#1c293e] bg-[#070b13] px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/40 outline-none transition"
                    required
                  />
                </label>
                <label className="block">
                  <span className="block text-xs font-medium text-slate-300 mb-1">Branch</span>
                  <input
                    type="text"
                    placeholder="main"
                    value={selectedBranch}
                    onChange={(e) => setSelectedBranch(e.target.value)}
                    className="w-full rounded border border-[#1c293e] bg-[#070b13] px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/40 outline-none transition"
                  />
                </label>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2 border-t border-[#1b273d]">
              <Button type="button" variant="outline" size="sm" onClick={() => setShowImportModal(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="sm" isLoading={isImporting}>
                Import Repository
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Imported Repositories List Table */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#080d17] text-slate-400 uppercase tracking-wider text-[10px] border-b border-[#1b273d]">
              <tr>
                <th className="py-3 px-4">Repository</th>
                <th className="py-3 px-4">Default Branch</th>
                <th className="py-3 px-4">Language</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#172235]">
              {(!Array.isArray(importedRepos) || importedRepos.length === 0) ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    No repositories imported yet. Click &apos;Add GitHub Repo&apos; above to get started.
                  </td>
                </tr>
              ) : (
                importedRepos.map((repo) => {
                  const isSelected = activeRepo?.id === repo.id;
                  return (
                    <tr
                      key={repo.id}
                      className={`hover:bg-[#11192b] transition-all duration-200 transform hover:scale-[1.006] ${
                        isSelected ? "bg-emerald-950/25 border-l-2 border-emerald-400" : ""
                      }`}
                    >
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2.5">
                          <GitBranch size={16} className={isSelected ? "text-emerald-400" : "text-slate-500"} />
                          <div>
                            <span className="font-bold text-slate-100">{repo.fullName || repo.name}</span>
                            {isSelected && (
                              <span className="ml-2 rounded-full bg-emerald-950/80 border border-emerald-500/40 px-2 py-0.2 text-[9px] font-semibold text-emerald-300 font-mono">
                                Active
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-emerald-400">{repo.defaultBranch}</td>
                      <td className="py-3 px-4">
                        <span className="rounded bg-[#070b13] border border-[#1c293e] px-2 py-0.5 text-[10px] text-slate-300 font-medium">
                          {repo.language || "Python"}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-950/70 border border-emerald-500/40 px-2.5 py-0.5 text-[10px] font-semibold text-emerald-300 font-mono">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_#00ff88]" />
                          Ready
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        <button
                          onClick={() => {
                            onSelectRepo(repo);
                            onNavigateToDashboard();
                          }}
                          className="font-semibold text-emerald-400 hover:text-emerald-300 transition-all duration-150 transform hover:scale-110 hover:translate-x-1 inline-block text-xs cursor-pointer"
                        >
                          View Dashboard &rarr;
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
