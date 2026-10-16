import React, { FormEvent, useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, GitBranch, Github, RefreshCw, Sparkles } from "lucide-react";
import { RemoteRepository, Repository as RepoType } from "../types";
import { githubApi } from "../services/githubApi";
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

export function RepositoryPage({
  importedRepos,
  activeRepo,
  onSelectRepo,
  onRepoImported,
  onNavigateToDashboard,
  showImportModal,
  setShowImportModal,
}: RepositoryPageProps) {
  const [importMode, setImportMode] = useState<"select" | "manual">("select");
  const [githubUsername, setGithubUsername] = useState("Ajaymallavali");
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

  async function fetchRemoteRepos(username: string) {
    setIsLoadingRemote(true);
    setRemoteError("");
    try {
      const data = await githubApi.getRemoteRepositories(username.trim());
      setRemoteRepos(data);
      if (data.length > 0) {
        setSelectedRemote(data[0]);
        loadBranches(data[0].fullName || data[0].full_name || data[0].name);
      }
    } catch (err) {
      setRemoteError(err instanceof Error ? err.message : "Failed to load repositories from GitHub.");
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
      setBranches(b);
      if (b.length > 0) {
        setSelectedBranch(b.includes("main") ? "main" : b[0]);
      }
    } catch {
      setBranches(["main"]);
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
      if (importMode === "select" && selectedRemote) {
        repo = await githubApi.importRepository({
          name: selectedRemote.name,
          fullName: selectedRemote.fullName || selectedRemote.full_name || selectedRemote.name,
          defaultBranch: selectedBranch,
          language: selectedRemote.language,
          githubId: selectedRemote.id,
        });
      } else {
        const trimmed = manualName.trim();
        if (!trimmed) throw new Error("Repository name is required.");
        repo = await githubApi.importRepository({
          name: trimmed.split("/").pop() || trimmed,
          fullName: trimmed.includes("/") ? trimmed : `user/${trimmed}`,
          defaultBranch: selectedBranch || "main",
          language: "Python",
        });
      }

      onRepoImported(repo);
      setImportSuccess(`Repository '${repo.fullName}' imported successfully!`);
      setTimeout(() => {
        setShowImportModal(false);
        setImportSuccess("");
      }, 1200);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import repository.");
    } finally {
      setIsImporting(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="rounded border border-slate-200 bg-white p-5 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900">Your Imported Repositories</h2>
          <p className="text-xs text-slate-500 mt-0.5">
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
        <Card className="border-teal-200 bg-teal-50/40 p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-teal-200 pb-3">
            <div className="flex items-center gap-2">
              <Github size={18} className="text-teal-800" />
              <h3 className="font-bold text-sm text-slate-900">Import GitHub Repository</h3>
            </div>
            <button
              onClick={() => setShowImportModal(false)}
              className="text-xs text-slate-400 hover:text-slate-600 font-semibold"
            >
              ✕ Close
            </button>
          </div>

          {/* Mode Switcher */}
          <div className="flex gap-4 border-b border-slate-200 pb-2">
            <button
              type="button"
              onClick={() => setImportMode("select")}
              className={`pb-1 text-xs font-semibold ${
                importMode === "select" ? "border-b-2 border-teal-800 text-teal-900" : "text-slate-500"
              }`}
            >
              Choose from my Repositories
            </button>
            <button
              type="button"
              onClick={() => setImportMode("manual")}
              className={`pb-1 text-xs font-semibold ${
                importMode === "manual" ? "border-b-2 border-teal-800 text-teal-900" : "text-slate-500"
              }`}
            >
              Import by Name (Public / Custom)
            </button>
          </div>

          {importSuccess && (
            <div className="flex items-center gap-2 rounded border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800 font-medium">
              <CheckCircle2 size={16} />
              <span>{importSuccess}</span>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 rounded border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleImportSubmit} className="space-y-4">
            {importMode === "select" ? (
              <div className="space-y-3">
                {/* GitHub Account Fetch Bar */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 p-2.5 bg-slate-50 rounded border border-slate-200">
                  <div className="flex items-center gap-1.5 text-xs text-slate-700 font-semibold shrink-0">
                    <Github size={15} className="text-slate-900" />
                    <span>GitHub Account:</span>
                  </div>
                  <input
                    type="text"
                    value={githubUsername}
                    onChange={(e) => setGithubUsername(e.target.value)}
                    placeholder="e.g. Ajaymallavali"
                    className="flex-1 rounded border border-slate-300 bg-white px-2.5 py-1 text-xs focus:border-slate-900 outline-none"
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

                {isLoadingRemote ? (
                  <Loader message={`Loading repositories for ${githubUsername}...`} size="sm" />
                ) : remoteError ? (
                  <div className="rounded border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                    <p className="font-semibold mb-1">GitHub Fetch Notice:</p>
                    <p>{remoteError}</p>
                    <p className="mt-1 text-[11px] text-amber-700">
                      You can also use the <strong>Import by Name</strong> tab to directly import any public repository.
                    </p>
                  </div>
                ) : null}

                {remoteRepos.length > 0 && (
                  <div className="grid gap-4 sm:grid-cols-2 pt-1">
                    <label className="block">
                      <span className="block text-xs font-medium text-slate-700 mb-1">Select Remote Repository</span>
                      <select
                        className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 outline-none"
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
                          <option key={r.id} value={r.id}>
                            {r.fullName || r.full_name || r.name} ({r.language || "Other"})
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="block">
                      <span className="block text-xs font-medium text-slate-700 mb-1">Default Branch</span>
                      <select
                        className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 outline-none"
                        value={selectedBranch}
                        onChange={(e) => setSelectedBranch(e.target.value)}
                        disabled={isLoadingBranches}
                      >
                        {branches.map((b) => (
                          <option key={b} value={b}>
                            {b}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                )}
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block">
                  <span className="block text-xs font-medium text-slate-700 mb-1">Repository Full Name</span>
                  <input
                    type="text"
                    placeholder="e.g. pallets/flask or owner/repo"
                    value={manualName}
                    onChange={(e) => setManualName(e.target.value)}
                    className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 outline-none"
                    required
                  />
                </label>
                <label className="block">
                  <span className="block text-xs font-medium text-slate-700 mb-1">Branch</span>
                  <input
                    type="text"
                    placeholder="main"
                    value={selectedBranch}
                    onChange={(e) => setSelectedBranch(e.target.value)}
                    className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 outline-none"
                  />
                </label>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-200">
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
            <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider text-[10px] border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Repository</th>
                <th className="py-3 px-4">Default Branch</th>
                <th className="py-3 px-4">Language</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {importedRepos.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-400">
                    No repositories imported yet. Click &apos;Add GitHub Repo&apos; above to get started.
                  </td>
                </tr>
              ) : (
                importedRepos.map((repo) => {
                  const isSelected = activeRepo?.id === repo.id;
                  return (
                    <tr key={repo.id} className={`hover:bg-slate-50 transition ${isSelected ? "bg-teal-50/40" : ""}`}>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <GitBranch size={16} className={isSelected ? "text-teal-700" : "text-slate-400"} />
                          <div>
                            <span className="font-bold text-slate-900">{repo.fullName || repo.name}</span>
                            {isSelected && (
                              <span className="ml-2 rounded-full bg-teal-100 px-2 py-0.2 text-[9px] font-semibold text-teal-800">
                                Active
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-600">{repo.defaultBranch}</td>
                      <td className="py-3 px-4">
                        <span className="rounded bg-slate-100 border border-slate-200 px-2 py-0.5 text-[10px] text-slate-700 font-medium">
                          {repo.language || "Python"}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-2.5 py-0.5 text-[10px] font-semibold text-emerald-800">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                          Ready
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        <button
                          onClick={() => {
                            onSelectRepo(repo);
                            onNavigateToDashboard();
                          }}
                          className="font-semibold text-teal-700 hover:text-teal-900 transition text-xs"
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
