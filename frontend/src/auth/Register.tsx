import React, { FormEvent, useState } from "react";
import { Lock, Mail, UserRound, AlertCircle } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { OAuthButtons } from "./OAuthButtons";

interface RegisterProps {
  onSwitchMode: (mode: "login" | "register" | "forgot") => void;
}

export function Register({ onSwitchMode }: RegisterProps) {
  const { register } = useAuth();
  const [displayName, setDisplayName] = useState("Ajay Kumar");
  const [email, setEmail] = useState("ajay@example.com");
  const [password, setPassword] = useState("codesense123");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ displayName?: string; email?: string; password?: string }>({});

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setFieldErrors({});

    const errs: { displayName?: string; email?: string; password?: string } = {};
    if (displayName.trim().length < 2) errs.displayName = "Name must be at least 2 characters.";
    if (!email.trim() || !email.includes("@")) errs.email = "Enter a valid email address.";
    if (password.length < 8) errs.password = "Password must be at least 8 characters.";

    if (Object.keys(errs).length > 0) {
      setFieldErrors(errs);
      return;
    }

    setIsLoading(true);
    try {
      await register(displayName.trim(), email.trim().toLowerCase(), password);
    } catch (err: any) {
      setError(err?.message || "Registration failed. Please try again.");
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
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">Create your CodeSense account</h2>
        <p className="text-xs text-slate-500 mt-1">Start auditing code health and running automated PR reviews</p>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
          <AlertCircle size={15} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3.5">
        <Input
          label="Full Name / Display Name"
          type="text"
          placeholder="Ajay Kumar"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          error={fieldErrors.displayName}
          icon={<UserRound size={15} />}
          required
        />

        <Input
          label="Work Email"
          type="email"
          placeholder="developer@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={fieldErrors.email}
          icon={<Mail size={15} />}
          required
        />

        <Input
          label="Password (min 8 characters)"
          type="password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={fieldErrors.password}
          icon={<Lock size={15} />}
          required
        />

        <Button type="submit" variant="primary" size="md" className="w-full mt-2" isLoading={isLoading}>
          Create Free Account
        </Button>
      </form>

      <OAuthButtons mode="register" onError={(msg) => setError(msg)} />

      <p className="text-center text-xs text-slate-500 pt-2">
        Already have an account?{" "}
        <button
          type="button"
          onClick={() => onSwitchMode("login")}
          className="font-semibold text-teal-700 hover:text-teal-900 transition"
        >
          Sign in
        </button>
      </p>
    </div>
  );
}
