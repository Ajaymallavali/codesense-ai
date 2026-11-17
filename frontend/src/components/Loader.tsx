import React from "react";
import { Loader2 } from "lucide-react";

interface LoaderProps {
  message?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function Loader({ message, size = "md", className = "" }: LoaderProps) {
  const pixelSizes = {
    sm: 16,
    md: 24,
    lg: 36,
  };

  return (
    <div className={`flex flex-col items-center justify-center gap-2 p-6 text-slate-400 ${className}`}>
      <Loader2 className="animate-spin text-emerald-400" size={pixelSizes[size]} />
      {message && <p className="text-xs font-medium text-emerald-300/90 animate-pulse">{message}</p>}
    </div>
  );
}
