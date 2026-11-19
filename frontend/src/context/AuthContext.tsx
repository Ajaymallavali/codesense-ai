import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { AuthResponse, User } from "../types";
import { authApi } from "../services/authApi";
import { AUTH_STORAGE_KEY } from "../services/apiClient";
import { DEFAULT_DEMO_USER } from "../services/fallbackData";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (displayName: string, email: string, password: string) => Promise<void>;
  loginWithGoogle: (credential: string) => Promise<void>;
  loginWithGithub: (payload?: { username?: string; token?: string; email?: string; displayName?: string }) => Promise<void>;
  logout: () => void;
  updateUser: (user: User) => void;
  refreshUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize auth state from localStorage and URL OAuth params
  useEffect(() => {
    // 1. Check for incoming OAuth redirect query parameters
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const oauthToken = urlParams.get("token");
      const githubConnected = urlParams.get("github_connected");
      const ghUsername = urlParams.get("username") || "Ajaymallavali";

      if (oauthToken) {
        const initialGhAuth: AuthResponse = {
          token: oauthToken,
          tokenType: "Bearer",
          user: {
            id: "github-session-user",
            displayName: ghUsername === "Ajaymallavali" ? "Ajay Mallavalli" : ghUsername,
            email: `${ghUsername.toLowerCase()}@github.com`,
            githubUsername: ghUsername,
            createdAt: new Date().toISOString(),
          },
        };
        setUser(initialGhAuth.user);
        setToken(initialGhAuth.token);
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(initialGhAuth));

        // Clean the address bar URL
        window.history.replaceState({}, document.title, window.location.pathname);

        // Fetch verified full profile from /api/auth/me
        authApi
          .getMe()
          .then((me) => {
            updateUser(me);
          })
          .catch((err) => {
            console.warn("Could not refresh GitHub user profile:", err);
          });

        setIsLoading(false);
        return;
      }
    } catch (err) {
      console.warn("OAuth parameter parsing error:", err);
    }

    // 2. Read from persistent local storage
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
    try {
      const auth = await authApi.login({ email, password });
      handleAuthSuccess(auth);
    } catch (err: any) {
      if (err?.status === 405 || err?.status === 404 || err?.status === 0 || !err?.status) {
        console.warn("Backend API not reachable or returned 405. Launching local session.", err);
        const fallbackAuth: AuthResponse = {
          token: "codesense_session_" + Date.now(),
          tokenType: "Bearer",
          user: {
            ...DEFAULT_DEMO_USER,
            email: email.trim() || DEFAULT_DEMO_USER.email,
            displayName: email.includes("@") ? email.split("@")[0] : DEFAULT_DEMO_USER.displayName,
          },
        };
        handleAuthSuccess(fallbackAuth);
        return;
      }
      throw err;
    }
  }

  async function register(displayName: string, email: string, password: string) {
    try {
      const auth = await authApi.register({ displayName, email, password });
      handleAuthSuccess(auth);
    } catch (err: any) {
      if (err?.status === 405 || err?.status === 404 || err?.status === 0 || !err?.status) {
        const fallbackAuth: AuthResponse = {
          token: "codesense_session_" + Date.now(),
          tokenType: "Bearer",
          user: {
            ...DEFAULT_DEMO_USER,
            displayName: displayName.trim() || DEFAULT_DEMO_USER.displayName,
            email: email.trim() || DEFAULT_DEMO_USER.email,
          },
        };
        handleAuthSuccess(fallbackAuth);
        return;
      }
      throw err;
    }
  }

  async function loginWithGoogle(credential: string) {
    try {
      const auth = await authApi.googleAuth(credential);
      handleAuthSuccess(auth);
    } catch (err: any) {
      if (err?.status === 405 || err?.status === 404 || err?.status === 0 || !err?.status) {
        console.warn("Backend API not reachable. Launching Google demo session.", err);
        const fallbackAuth: AuthResponse = {
          token: "codesense_google_session_" + Date.now(),
          tokenType: "Bearer",
          user: DEFAULT_DEMO_USER,
        };
        handleAuthSuccess(fallbackAuth);
        return;
      }
      throw err;
    }
  }

  async function loginWithGithub(payload?: { username?: string; token?: string; email?: string; displayName?: string }) {
    try {
      const auth = await authApi.loginWithGithub(payload);
      handleAuthSuccess(auth);
    } catch (err: any) {
      if (err?.status === 405 || err?.status === 404 || err?.status === 0 || !err?.status) {
        console.warn("Backend API not reachable. Launching GitHub demo session.", err);
        const fallbackAuth: AuthResponse = {
          token: "codesense_github_session_" + Date.now(),
          tokenType: "Bearer",
          user: {
            ...DEFAULT_DEMO_USER,
            githubUsername: payload?.username || "Ajaymallavali",
            displayName: payload?.displayName || "Ajay Mallavalli",
            email: payload?.email || `${(payload?.username || "ajaymallavali").toLowerCase()}@github.com`,
          },
        };
        handleAuthSuccess(fallbackAuth);
        return;
      }
      throw err;
    }
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
        loginWithGithub,
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
