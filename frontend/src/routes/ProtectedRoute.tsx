import React, { ReactNode, useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { Loader } from "../components/Loader";
import { AuthLayout } from "../layouts/AuthLayout";
import { Login } from "../auth/Login";
import { Register } from "../auth/Register";
import { ForgotPassword } from "../auth/ForgotPassword";
import { AuthMode } from "../types";

interface ProtectedRouteProps {
  children: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const [authMode, setAuthMode] = useState<AuthMode>("login");

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader message="Loading CodeSense session..." size="lg" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <AuthLayout>
        {authMode === "login" && <Login onSwitchMode={setAuthMode} />}
        {authMode === "register" && <Register onSwitchMode={setAuthMode} />}
        {authMode === "forgot" && <ForgotPassword onBackToLogin={() => setAuthMode("login")} />}
      </AuthLayout>
    );
  }

  return <>{children}</>;
}
