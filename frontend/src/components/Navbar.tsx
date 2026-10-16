import React from "react";
import { FileText, GitBranch, LogOut } from "lucide-react";
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
      title: "Gemini AI Review Engine",
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
    <header className="border-b border-slate-200 bg-white px-5 py-4 sm:px-8">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs text-slate-500 font-medium">
            Signed in as <span className="font-semibold text-slate-700">{user.displayName}</span>
            {user.githubUsername && (
              <span className="ml-1 text-[11px] rounded bg-slate-100 px-1.5 py-0.5 text-slate-600 font-mono">
                @{user.githubUsername}
              </span>
            )}
          </p>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight mt-0.5">
            {current.title}
          </h1>
          <p className="text-xs text-slate-500 mt-1">{current.subtitle}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
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
