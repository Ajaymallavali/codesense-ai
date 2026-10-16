import React, { ReactNode } from "react";
import { Activity, Bug, CheckCircle2, ShieldCheck, Sparkles } from "lucide-react";

interface AuthLayoutProps {
  children: ReactNode;
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex items-center justify-center gap-3 mb-6">
          <div className="grid h-12 w-12 place-items-center rounded-xl bg-teal-800 text-xl font-bold text-white shadow-md">
            CS
          </div>
          <div>
            <h1 className="text-xl font-extrabold tracking-tight text-slate-900 uppercase">
              CodeSense <span className="text-teal-700">AI</span>
            </h1>
            <p className="text-xs text-slate-500 font-medium">Next-Gen Code Quality &amp; PR Review Intelligence</p>
          </div>
        </div>

        <div className="bg-white py-8 px-6 shadow-sm rounded-xl border border-slate-200 sm:px-10">
          {children}
        </div>

        {/* Feature Pills Footer */}
        <div className="mt-8 flex flex-wrap items-center justify-center gap-4 text-xs text-slate-500">
          <span className="flex items-center gap-1.5">
            <ShieldCheck size={14} className="text-teal-700" /> AST Security Audits
          </span>
          <span className="flex items-center gap-1.5">
            <Activity size={14} className="text-teal-700" /> Real Maintainability Index
          </span>
          <span className="flex items-center gap-1.5">
            <Sparkles size={14} className="text-teal-700" /> Gemini PR Reviews
          </span>
        </div>
      </div>
    </div>
  );
}
