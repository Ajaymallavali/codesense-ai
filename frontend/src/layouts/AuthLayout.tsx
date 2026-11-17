import React, { ReactNode } from "react";
import { Activity, Bug, CheckCircle2, ShieldCheck, Sparkles } from "lucide-react";
import { CyberBackground } from "../components/CyberBackground";

interface AuthLayoutProps {
  children: ReactNode;
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen bg-[#080c14] text-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative selection:bg-emerald-500/30 selection:text-emerald-200">
      {/* High-Tech Cyber Dynamic Background & Plasma Glows */}
      <CyberBackground />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10 animate-fade-in">
        <div className="flex items-center justify-center gap-3 mb-6">
          <div className="grid h-12 w-12 place-items-center rounded-xl bg-gradient-to-br from-emerald-400 to-teal-700 text-xl font-black text-slate-950 shadow-[0_0_20px_rgba(16,185,129,0.4)]">
            CS
          </div>
          <div>
            <h1 className="text-xl font-extrabold tracking-tight text-slate-100 uppercase flex items-center gap-1.5">
              <span>CodeSense</span> <span className="text-emerald-400 drop-shadow-[0_0_8px_#00ff88]">AI</span>
            </h1>
            <p className="text-xs text-slate-400 font-medium">Next-Gen Code Quality &amp; PR Review Intelligence</p>
          </div>
        </div>

        <div className="bg-[#0d1424] py-8 px-6 shadow-cyber rounded-xl border border-[#1b273d] sm:px-10">
          {children}
        </div>

        {/* Feature Pills Footer */}
        <div className="mt-8 flex flex-wrap items-center justify-center gap-4 text-xs text-slate-400">
          <span className="flex items-center gap-1.5 text-slate-300">
            <ShieldCheck size={14} className="text-emerald-400" /> AST Security Audits
          </span>
          <span className="flex items-center gap-1.5 text-slate-300">
            <Activity size={14} className="text-emerald-400" /> Real Maintainability Index
          </span>
          <span className="flex items-center gap-1.5 text-slate-300">
            <Sparkles size={14} className="text-emerald-400" /> Qwen3-Coder PR Reviews
          </span>
        </div>
      </div>
    </div>
  );
}
