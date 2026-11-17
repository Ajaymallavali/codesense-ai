import React from "react";
import { FileText, GitBranch, LogOut, User as UserIcon } from "lucide-react";
import { User } from "../types";
import { Button } from "./Button";

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
              <span className="text-[11px] rounded bg-emerald-950/60 border border-emerald-500/30 px-1.5 py-0.5 text-emerald-300 font-mono transition-transform duration-200 hover:scale-105">
                @{user.githubUsername}
              </span>
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
    </header>
  );
}
