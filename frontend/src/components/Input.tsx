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
      {label && <span className="block text-xs font-medium text-slate-700 mb-1">{label}</span>}
      <span
        className={`flex items-center gap-2.5 rounded border bg-white px-3 py-2 text-xs text-slate-800 transition focus-within:border-slate-900 ${
          error ? "border-rose-400 bg-rose-50/20" : "border-slate-300"
        } ${props.readOnly ? "bg-slate-50 text-slate-500 cursor-not-allowed" : ""} ${className}`}
      >
        {icon && <span className="text-slate-400 shrink-0">{icon}</span>}
        <input
          type={inputType}
          className="w-full bg-transparent border-0 p-0 text-xs outline-none placeholder:text-slate-400"
          {...props}
        />
        {isPassword && !props.readOnly && (
          <button
            type="button"
            onClick={() => setShowPassword((prev) => !prev)}
            className="text-slate-400 hover:text-slate-600 focus:outline-none"
            title={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        )}
      </span>
      {error && <span className="block text-[11px] text-rose-600 mt-1 font-medium">{error}</span>}
    </label>
  );
}
