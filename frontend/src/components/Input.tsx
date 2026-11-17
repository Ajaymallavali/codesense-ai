import React, { InputHTMLAttributes, ReactNode, useState } from "react";
import { Eye, EyeOff } from "lucide-react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: ReactNode;
}

export function Input({ label, error, icon, type = "text", className = "", ...props }: InputProps) {
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === "password";
  const inputType = isPassword ? (showPassword ? "text" : "password") : type;

  return (
    <label className="block w-full">
      {label && <span className="block text-xs font-medium text-slate-300 mb-1">{label}</span>}
      <span
        className={`flex items-center gap-2.5 rounded-md border bg-[#090e1a] px-3 py-2 text-xs text-slate-100 transition-all duration-200 transform focus-within:scale-[1.01] focus-within:border-emerald-500 focus-within:ring-1 focus-within:ring-emerald-500/40 focus-within:shadow-[0_0_15px_rgba(16,185,129,0.25)] ${
          error ? "border-rose-500/60 bg-rose-950/30" : "border-[#1c293e]"
        } ${props.readOnly ? "bg-[#060a12] text-slate-500 cursor-not-allowed" : ""} ${className}`}
      >
        {icon && <span className="text-slate-400 shrink-0 transition-transform duration-200 group-hover:scale-110">{icon}</span>}
        <input
          type={inputType}
          className="w-full bg-transparent border-0 p-0 text-xs text-slate-100 outline-none placeholder:text-slate-500"
          {...props}
        />
        {isPassword && !props.readOnly && (
          <button
            type="button"
            onClick={() => setShowPassword((prev) => !prev)}
            className="text-slate-400 hover:text-emerald-400 focus:outline-none transition-all duration-150 transform hover:scale-115 active:scale-90"
            title={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        )}
      </span>
      {error && <span className="block text-[11px] text-rose-400 mt-1 font-medium">{error}</span>}
    </label>
  );
}
