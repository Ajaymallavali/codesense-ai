import React from "react";
import { Activity, FileText, GitBranch, MessageSquare, Settings } from "lucide-react";

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: Activity },
    { id: "repositories", label: "Repositories", icon: GitBranch },
    { id: "review", label: "AI Review", icon: MessageSquare },
    { id: "reports", label: "Reports", icon: FileText },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  return (
    <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-200 bg-white px-5 py-6 lg:block z-30">
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded bg-teal-800 text-lg font-bold text-white shadow-sm">
          CS
        </div>
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-teal-900">CodeSense</p>
          <p className="text-xs text-slate-500">AI Code Quality &amp; PR</p>
        </div>
      </div>

      <nav className="mt-8 space-y-1 text-sm font-medium">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`flex w-full items-center gap-3 rounded px-3 py-2.5 text-left text-xs font-semibold transition-all ${
                isActive
                  ? "bg-slate-900 text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
              }`}
            >
              <Icon size={17} className={isActive ? "text-teal-400" : "text-slate-400"} />
              {item.label}
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
