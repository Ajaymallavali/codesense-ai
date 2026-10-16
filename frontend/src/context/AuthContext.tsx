import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { AuthResponse, User } from "../types";
import { authApi } from "../services/authApi";
import { AUTH_STORAGE_KEY } from "../services/apiClient";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (displayName: string, email: string, password: string) => Promise<void>;
  loginWithGoogle: (credential: string) => Promise<void>;
  logout: () => void;
  updateUser: (user: User) => void;
  refreshUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize auth state from localStorage
  useEffect(() => {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (raw) {
      try {
        const parsed: AuthResponse = JSON.parse(raw);
        setUser(parsed.user);
        setToken(parsed.token);
      } catch {
        localStorage.removeItem(AUTH_STORAGE_KEY);
      }
    }
    // Listen for unauthorized events to clear dead sessions
    const handleUnauthorized = () => {
      setUser(null);
      setToken(null);
    };
    window.addEventListener("codesense:unauthorized", handleUnauthorized);

    setIsLoading(false);
    return () => {
      window.removeEventListener("codesense:unauthorized", handleUnauthorized);
    };
  }, []);

  function handleAuthSuccess(auth: AuthResponse) {
    setUser(auth.user);
    setToken(auth.token);
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth));
  }

  async function login(email: string, password: string) {
    const auth = await authApi.login({ email, password });
    handleAuthSuccess(auth);
  }

  async function register(displayName: string, email: string, password: string) {
    const auth = await authApi.register({ displayName, email, password });
    handleAuthSuccess(auth);
  }

  async function loginWithGoogle(credential: string) {
    const auth = await authApi.googleAuth(credential);
    handleAuthSuccess(auth);
  }

  function logout() {
    setUser(null);
    setToken(null);
    localStorage.removeItem(AUTH_STORAGE_KEY);
  }

  function updateUser(updatedUser: User) {
    setUser(updatedUser);
    if (token) {
      localStorage.setItem(
        AUTH_STORAGE_KEY,
        JSON.stringify({
          token,
          tokenType: "Bearer",
          user: updatedUser,
        })
      );
    }
  }

  async function refreshUser() {
    try {
      const refreshed = await authApi.getMe();
      updateUser(refreshed);
    } catch {
      // Ignore if session expired or failed
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        register,
        loginWithGoogle,
        logout,
        updateUser,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuthContext must be used within an AuthProvider");
  }
  return context;
}
