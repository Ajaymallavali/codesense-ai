import React, { useState } from "react";
import { FileText, GitBranch, LogOut, User as UserIcon, Github, X, Loader2 } from "lucide-react";
import { User } from "../types";
import { Button } from "./Button";
import { useAuth } from "../hooks/useAuth";

interface NavbarProps {
  user: User;
  activeTab: string;
  onNavigate: (tab: string) => void;
  onOpenImportModal: () => void;
  onLogout: () => void;
}

export function Navbar({
  user,
  activeTab,
  onNavigate,
  onOpenImportModal,
  onLogout,
}: NavbarProps) {
  const { updateUser } = useAuth();
  const [isSwitchOpen, setIsSwitchOpen] = useState(false);
  const [switchUsername, setSwitchUsername] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifiedInfo, setVerifiedInfo] = useState<{
    login: string;
    name: string | null;
    avatar_url: string;
    public_repos: number;
  } | null>(null);

  const handleVerify = async (username: string) => {
    const clean = username.trim().replace(/^@/, "");
    if (!clean) return;
    setIsVerifying(true);
    try {
      const res = await fetch(`https://api.github.com/users/${encodeURIComponent(clean)}`);
      if (res.ok) {
        const data = await res.json();
        setVerifiedInfo({
          login: data.login,
          name: data.name,
          avatar_url: data.avatar_url,
          public_repos: data.public_repos || 0,
        });
      } else {
        setVerifiedInfo({
          login: clean,
          name: clean,
          avatar_url: `https://github.com/${clean}.png`,
          public_repos: 0,
        });
      }
    } catch {
      setVerifiedInfo({
        login: clean,
        name: clean,
        avatar_url: `https://github.com/${clean}.png`,
        public_repos: 0,
      });
    } finally {
      setIsVerifying(false);
    }
  };

  const handleConfirmSwitch = () => {
    if (!verifiedInfo) return;
    updateUser({
      ...user,
      githubUsername: verifiedInfo.login,
      displayName:
        verifiedInfo.name ||
        (verifiedInfo.login.toLowerCase() === "ajaymallavali"
          ? "Ajay Mallavalli"
          : verifiedInfo.login),
      email: `${verifiedInfo.login.toLowerCase()}@users.noreply.github.com`,
    });
    setIsSwitchOpen(false);
    setVerifiedInfo(null);
    setSwitchUsername("");
    window.location.reload();
  };

  const titles: Record<string, { title: string; subtitle: string }> = {
    dashboard: {
      title: "Repository Quality Dashboard",
      subtitle: "Live maintainability, security risks, complexity, and historical debt metrics",
    },
    repositories: {
      title: "GitHub Repositories",
      subtitle: "Connect and manage your imported repositories and branches",
    },
    review: {
      title: "Qwen3-Coder AI Review Engine",
      subtitle: "AST-enriched code review, targeted remediations, and automated PR reviews",
    },
    reports: {
      title: "Quality & Security Reports",
      subtitle: "Generate, inspect, and export comprehensive code health assessments",
    },
    settings: {
      title: "Workspace & Profile Settings",
      subtitle: "Manage your profile, GitHub Personal Access Token (PAT), and account password",
    },
  };

  const current = titles[activeTab] || {
    title: "CodeSense AI",
    subtitle: "AI-Powered Code Review and Quality Intelligence",
  };

  return (
    <header className="border-b border-[#172235] bg-[#0a0e18]/90 backdrop-blur-md px-5 py-4 sm:px-8 sticky top-0 z-20">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-400 font-medium">
            <UserIcon size={13} className="text-emerald-400 transition-transform hover:scale-125" />
            <span>Signed in as <span className="font-semibold text-slate-200">{user.displayName}</span></span>
            {user.githubUsername && (
              <button
                type="button"
                onClick={() => setIsSwitchOpen(true)}
                className="text-[11px] rounded bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 text-emerald-300 font-mono transition-transform duration-200 hover:scale-105 hover:bg-emerald-900/60 cursor-pointer flex items-center gap-1.5"
                title="Click to switch or connect any GitHub account"
              >
                <span>@{user.githubUsername}</span>
                <span className="text-[10px] text-emerald-400/80 underline font-sans">Switch</span>
              </button>
            )}
          </div>
          <div key={activeTab} className="animate-fade-in">
            <h1 className="text-xl sm:text-2xl font-black text-slate-100 tracking-tight mt-1 flex items-center gap-2">
              {current.title}
            </h1>
            <p className="text-xs text-slate-400 mt-1">{current.subtitle}</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="primary"
            size="sm"
            icon={<GitBranch size={15} />}
            onClick={onOpenImportModal}
          >
            Import Repository
          </Button>

          <Button
            variant="outline"
            size="sm"
            icon={<FileText size={15} />}
            onClick={() => onNavigate("reports")}
          >
            Export Report
          </Button>

          <Button
            variant="ghost"
            size="sm"
            icon={<LogOut size={15} />}
            onClick={onLogout}
          >
            Logout
          </Button>
        </div>
      </div>

      {/* Switch GitHub Account Modal */}
      {isSwitchOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-fade-in">
          <div className="relative w-full max-w-sm rounded-2xl border border-emerald-500/40 bg-[#0c1424] p-5 shadow-2xl text-slate-100 space-y-4 animate-scale-in">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Github size={20} className="text-emerald-400" />
                <h3 className="text-sm font-bold text-slate-100">Switch GitHub Account</h3>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsSwitchOpen(false);
                  setVerifiedInfo(null);
                }}
                className="p-1 rounded text-slate-400 hover:text-slate-200"
              >
                <X size={16} />
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Enter any GitHub handle (e.g. <span className="text-emerald-300 font-mono">Ajaymallavali</span>, <span className="text-emerald-300 font-mono">Sravannii-24</span>, or recruiter handle) to load their repositories.
            </p>

            <div className="space-y-2">
              <div className="relative">
                <input
                  type="text"
                  value={switchUsername}
                  onChange={(e) => {
                    setSwitchUsername(e.target.value);
                    if (e.target.value.trim().length > 1) {
                      handleVerify(e.target.value);
                    } else {
                      setVerifiedInfo(null);
                    }
                  }}
                  placeholder="e.g. Ajaymallavali, Sravannii-24"
                  className="w-full rounded-lg border border-[#1e2d42] bg-[#05080f] px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:outline-none font-mono"
                  autoFocus
                />
                {isVerifying && (
                  <Loader2 size={13} className="absolute right-3 top-2.5 text-emerald-400 animate-spin" />
                )}
              </div>

              {verifiedInfo && (
                <div className="flex items-center gap-2.5 rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-2 text-xs">
                  <img
                    src={verifiedInfo.avatar_url}
                    alt={verifiedInfo.login}
                    className="w-8 h-8 rounded-full border border-emerald-400 object-cover"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-slate-200 truncate">{verifiedInfo.name || verifiedInfo.login}</p>
                    <p className="text-[10px] text-emerald-400 font-mono">@{verifiedInfo.login} • {verifiedInfo.public_repos} repos</p>
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setIsSwitchOpen(false);
                  setVerifiedInfo(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={!verifiedInfo}
                onClick={handleConfirmSwitch}
              >
                Switch & Load Repos
              </Button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
