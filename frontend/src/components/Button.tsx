import React, { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
  icon?: ReactNode;
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  isLoading = false,
  icon,
  className = "",
  disabled,
  ...props
}: ButtonProps) {
  const baseStyles =
    "inline-flex items-center justify-center font-semibold rounded-md transition-all duration-200 ease-out outline-none focus:ring-2 focus:ring-offset-1 focus:ring-offset-[#080c14] disabled:opacity-50 disabled:cursor-not-allowed select-none cursor-pointer transform hover:scale-[1.03] hover:-translate-y-0.5 active:scale-[0.96] active:translate-y-0";

  const sizeStyles = {
    sm: "px-2.5 py-1.5 text-xs gap-1.5",
    md: "px-3.5 py-2 text-xs sm:text-sm gap-2",
    lg: "px-5 py-2.5 text-sm sm:text-base gap-2.5",
  };

  const variantStyles = {
    primary:
      "bg-slate-900 text-emerald-400 border border-emerald-500/40 hover:bg-emerald-950/80 hover:text-emerald-300 hover:border-emerald-400 hover:shadow-neon focus:ring-emerald-500 shadow-sm",
    secondary:
      "bg-emerald-600 text-slate-950 font-bold hover:bg-emerald-500 hover:shadow-neon focus:ring-emerald-400 shadow-sm",
    outline:
      "border border-slate-300 bg-[#0d1424] text-slate-200 hover:bg-emerald-950/40 hover:text-emerald-300 hover:border-emerald-500/50 hover:shadow-[0_0_12px_rgba(16,185,129,0.2)] focus:ring-emerald-500",
    danger:
      "bg-rose-600 text-white hover:bg-rose-700 hover:shadow-[0_0_15px_rgba(244,63,94,0.4)] focus:ring-rose-600 shadow-sm",
    ghost:
      "bg-transparent text-slate-400 hover:bg-[#111a2e] hover:text-emerald-300 hover:shadow-[0_0_10px_rgba(16,185,129,0.15)] focus:ring-emerald-500",
  };

  return (
    <button
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="animate-spin text-emerald-400" size={size === "sm" ? 14 : 16} />
      ) : (
        icon && <span className="shrink-0 transition-transform duration-200 group-hover:scale-110">{icon}</span>
      )}
      <span>{children}</span>
    </button>
  );
}
