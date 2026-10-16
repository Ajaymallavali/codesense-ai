import React, { FormEvent, useState } from "react";
import { Lock, Mail, AlertCircle } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { OAuthButtons } from "./OAuthButtons";

interface LoginProps {
  onSwitchMode: (mode: "login" | "register" | "forgot") => void;
}

export function Login({ onSwitchMode }: LoginProps) {
  const { login } = useAuth();
  const [email, setEmail] = useState("ajay@example.com");
  const [password, setPassword] = useState("codesense123");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setFieldErrors({});

    const errs: { email?: string; password?: string } = {};
    if (!email.trim()) errs.email = "Email is required.";
    if (!password) errs.password = "Password is required.";

    if (Object.keys(errs).length > 0) {
      setFieldErrors(errs);
      return;
    }

    setIsLoading(true);
    try {
      await login(email.trim().toLowerCase(), password);
    } catch (err: any) {
      setError(err?.message || "Invalid email or password.");
      if (err?.fieldErrors) {
        setFieldErrors(err.fieldErrors);
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">Sign in to your workspace</h2>
        <p className="text-xs text-slate-500 mt-1">Enter your credentials to access your quality metrics</p>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
          <AlertCircle size={15} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3.5">
        <Input
          label="Email Address"
          type="email"
          placeholder="developer@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={fieldErrors.email}
          icon={<Mail size={15} />}
          required
        />

        <Input
          label="Password"
          type="password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={fieldErrors.password}
          icon={<Lock size={15} />}
          required
        />

        <div className="flex items-center justify-between text-xs">
          <label className="flex items-center gap-1.5 text-slate-600 cursor-pointer">
            <input type="checkbox" defaultChecked className="rounded border-slate-300 text-slate-900 focus:ring-0" />
            <span>Remember me</span>
          </label>
          <button
            type="button"
            onClick={() => onSwitchMode("forgot")}
            className="font-semibold text-teal-700 hover:text-teal-900 transition"
          >
            Forgot password?
          </button>
        </div>

        <Button type="submit" variant="primary" size="md" className="w-full mt-2" isLoading={isLoading}>
          Sign In
        </Button>
      </form>

      <OAuthButtons mode="login" onError={(msg) => setError(msg)} />

      <p className="text-center text-xs text-slate-500 pt-2">
        Don&apos;t have an account?{" "}
        <button
          type="button"
          onClick={() => onSwitchMode("register")}
          className="font-semibold text-teal-700 hover:text-teal-900 transition"
        >
          Create one now
        </button>
      </p>
    </div>
  );
}
