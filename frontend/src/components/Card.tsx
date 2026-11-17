import React, { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  action?: ReactNode;
}

export function Card({ children, className = "", title, subtitle, action }: CardProps) {
  return (
    <div className={`rounded-lg border border-[#1b273d] bg-[#0d1424] p-5 shadow-cyber transition-all duration-300 ease-out hover:border-emerald-500/40 text-slate-100 ${className}`}>
      {(title || subtitle || action) && (
        <div className="flex items-center justify-between border-b border-[#1b273d] pb-3 mb-4">
          <div>
            {title && <h3 className="text-base font-bold text-slate-100 tracking-tight">{title}</h3>}
            {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
          </div>
          {action && <div className="transition-transform duration-200 hover:scale-105">{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
}
