import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw, RotateCcw } from "lucide-react";
import { AUTH_STORAGE_KEY } from "../services/apiClient";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("CodeSense Uncaught React Error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  private handleHardReset = () => {
    try {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      sessionStorage.clear();
    } catch {}
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[400px] flex items-center justify-center p-6 select-none animate-fade-in">
          <div className="max-w-md w-full rounded-xl border border-emerald-500/30 bg-[#0d1424] p-6 shadow-[0_0_35px_rgba(0,0,0,0.8)] text-center space-y-4">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-950/60 border border-amber-500/40 text-amber-400 shadow-[0_0_20px_rgba(245,158,11,0.25)]">
              <AlertTriangle size={28} />
            </div>

            <div className="space-y-1.5">
              <h3 className="text-base font-bold text-slate-100">
                {this.props.fallbackTitle || "Workspace Rendering Notice"}
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                A display glitch occurred while rendering this component. CodeSense has contained the error safely.
              </p>
            </div>

            {this.state.error?.message && (
              <div className="rounded-lg bg-[#070b13] border border-[#1c293e] p-2.5 text-left overflow-x-auto text-[11px] font-mono text-rose-300">
                <span className="text-slate-500 block text-[9px] uppercase tracking-wider mb-1">Details:</span>
                {this.state.error.message}
              </div>
            )}

            <div className="flex items-center justify-center gap-3 pt-2">
              <button
                type="button"
                onClick={this.handleReset}
                className="inline-flex items-center gap-1.5 rounded-md bg-emerald-600 hover:bg-emerald-500 px-3.5 py-2 text-xs font-semibold text-slate-950 transition shadow-neon cursor-pointer"
              >
                <RefreshCw size={13} />
                <span>Retry View</span>
              </button>

              <button
                type="button"
                onClick={this.handleHardReset}
                className="inline-flex items-center gap-1.5 rounded-md border border-[#1c293e] hover:border-slate-600 bg-[#070b13] px-3.5 py-2 text-xs font-medium text-slate-300 hover:text-white transition cursor-pointer"
              >
                <RotateCcw size={13} />
                <span>Reset Session</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
