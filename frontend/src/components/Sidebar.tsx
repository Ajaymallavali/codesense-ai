import React from "react";
import { Activity, FileText, GitBranch, MessageSquare, Settings, Sparkles } from "lucide-react";

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
    <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-[#172235] bg-[#0a0e18] px-5 py-6 lg:block z-30 select-none">
      {/* Brand Header with Scale & Pulse */}
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-lg bg-gradient-to-br from-emerald-400 to-teal-700 text-lg font-black text-slate-950 shadow-[0_0_18px_rgba(16,185,129,0.45)] transition-all duration-300 hover:scale-110 active:scale-95 cursor-pointer">
          CS
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <p className="text-sm font-bold uppercase tracking-wider text-slate-100">CodeSense</p>
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500 shadow-[0_0_6px_#00ff88]"></span>
            </span>
          </div>
          <p className="text-[11px] text-emerald-400/80 font-mono">AI Code Quality &amp; PR</p>
        </div>
      </div>

      {/* Navigation with Scale Micro-interactions */}
      <nav className="mt-8 space-y-1.5 text-sm font-medium">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`group relative flex w-full items-center gap-3 rounded-md px-3.5 py-2.5 text-left text-xs font-semibold transition-all duration-200 ease-out transform hover:scale-[1.02] hover:translate-x-1 active:scale-[0.98] ${
                isActive
                  ? "bg-emerald-950/60 text-emerald-300 border border-emerald-500/40 shadow-[0_0_16px_rgba(16,185,129,0.2)]"
                  : "text-slate-400 hover:bg-[#11192b] hover:text-emerald-300 hover:border-[#1e2d45] hover:shadow-[0_0_10px_rgba(16,185,129,0.1)] border border-transparent"
              }`}
            >
              {/* Active glow accent bar */}
              {isActive && (
                <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r bg-emerald-400 shadow-[0_0_10px_#00ff88] transition-all duration-300" />
              )}
              <Icon
                size={17}
                className={`transition-all duration-200 transform group-hover:scale-125 ${
                  isActive ? "text-emerald-400 drop-shadow-[0_0_8px_rgba(16,185,129,0.7)]" : "text-slate-500 group-hover:text-emerald-400"
                }`}
              />
              <span className="truncate">{item.label}</span>
              {item.id === "review" && (
                <span className="ml-auto flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 transition-transform duration-200 group-hover:scale-110">
                  <Sparkles size={10} className="animate-pulse" />
                  AI
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer Info Pill with Hover Lift */}
      <div className="absolute bottom-6 left-5 right-5 rounded-lg border border-[#172235] bg-[#0c121e] p-3 text-[11px] text-slate-400 transition-all duration-300 hover:border-emerald-500/30 hover:shadow-[0_0_15px_rgba(16,185,129,0.12)] hover:scale-[1.02]">
        <div className="flex items-center justify-between text-xs font-medium text-slate-300 mb-1">
          <span className="flex items-center gap-1.5 text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_6px_#00ff88]" />
            Qwen3-Coder Active
          </span>
          <span className="text-[10px] text-slate-500 font-mono">v2.5</span>
        </div>
        <p className="text-[10px] text-slate-500 leading-snug">
          Cloudflare Workers AI &amp; AST Analysis Engine.
        </p>
      </div>
    </aside>
  );
}
