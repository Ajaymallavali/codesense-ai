import React, { useEffect, useRef, useState } from "react";
import { Github, ArrowRight, X, Key, User as UserIcon, Sparkles } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { authApi } from "../services/authApi";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
            auto_select?: boolean;
            cancel_on_tap_outside?: boolean;
          }) => void;
          renderButton: (
            parent: HTMLElement,
            options: {
              theme?: "outline" | "filled_blue" | "filled_black";
              size?: "large" | "medium" | "small";
              text?: "signin_with" | "signup_with" | "continue_with" | "signin";
              shape?: "rectangular" | "pill" | "circle" | "square";
              logo_alignment?: "left" | "center";
              width?: number | string;
            }
          ) => void;
          prompt: () => void;
        };
      };
    };
  }
}

interface OAuthButtonsProps {
  mode: "login" | "register";
  onError: (msg: string) => void;
}

export function OAuthButtons({ mode, onError }: OAuthButtonsProps) {
  const { loginWithGoogle, loginWithGithub } = useAuth();
  const googleBtnRef = useRef<HTMLDivElement>(null);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [isGithubLoading, setIsGithubLoading] = useState(false);
  const [showGithubModal, setShowGithubModal] = useState(false);
  const [customUsername, setCustomUsername] = useState("Ajaymallavali");
  const [customToken, setCustomToken] = useState("");
  const [showCustomFields, setShowCustomFields] = useState(false);
  const [oauthUrl, setOauthUrl] = useState<string | null>(null);
  const [isOauthConfigured, setIsOauthConfigured] = useState(false);

  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
  const isRealGoogleConfigured = Boolean(
    googleClientId &&
    googleClientId.trim() !== "" &&
    !googleClientId.includes("mock") &&
    googleClientId.includes(".apps.googleusercontent.com")
  );

  // Load Google Identity Services (GSI) script ONLY if a real Google Client ID is configured
  useEffect(() => {
    if (!isRealGoogleConfigured) {
      return;
    }

    let script = document.getElementById("google-gsi-script") as HTMLScriptElement | null;

    const initGsi = () => {
      if (window.google?.accounts?.id && googleBtnRef.current) {
        try {
          window.google.accounts.id.initialize({
            client_id: googleClientId,
            callback: async (response: { credential: string }) => {
              if (response.credential) {
                setIsGoogleLoading(true);
                try {
                  await loginWithGoogle(response.credential);
                } catch (err) {
                  onError(err instanceof Error ? err.message : "Google authentication failed.");
                } finally {
                  setIsGoogleLoading(false);
                }
              }
            },
          });

          // Render Google Sign-in button
          googleBtnRef.current.innerHTML = "";
          window.google.accounts.id.renderButton(googleBtnRef.current, {
            theme: "outline",
            size: "large",
            text: mode === "register" ? "signup_with" : "signin_with",
            width: 320,
          });
        } catch (err) {
          console.warn("GSI button initialization notice:", err);
        }
      }
    };

    if (!script) {
      script = document.createElement("script");
      script.id = "google-gsi-script";
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.onload = initGsi;
      document.body.appendChild(script);
    } else {
      initGsi();
    }
  }, [googleClientId, isRealGoogleConfigured, mode]);

  // Check backend GitHub OAuth configuration status on mount
  useEffect(() => {
    authApi
      .getGithubOAuthUrl()
      .then((info) => {
        if (info.configured && info.url) {
          setIsOauthConfigured(true);
          setOauthUrl(info.url);
        }
      })
      .catch(() => {
        // Fallback to direct sign-in silently
      });
  }, []);

  // Handle GitHub Click: If OAuth configured and user wants OAuth redirect, or open direct login modal
  async function handleGithubButtonClick() {
    setShowGithubModal(true);
  }

  // Execute Direct GitHub Account Login
  async function handleDirectGithubLogin(username: string, token?: string) {
    setIsGithubLoading(true);
    const cleaned = username
      .trim()
      .replace(/^https?:\/\/github\.com\//i, "")
      .replace(/^git@github\.com:/i, "")
      .replace(/\.git$/i, "")
      .split("/")[0]
      .replace(/[^a-zA-Z0-9_-]/g, "");

    try {
      await loginWithGithub({
        username: cleaned || "Ajaymallavali",
        token: token?.trim() || undefined,
      });
      setShowGithubModal(false);
    } catch (err) {
      onError(err instanceof Error ? err.message : "GitHub authentication failed.");
    } finally {
      setIsGithubLoading(false);
    }
  }

  // Handle Dev Google Mock Token (for testing without external Google Client ID)
  async function handleDevGoogleMockLogin() {
    setIsGoogleLoading(true);
    try {
      await loginWithGoogle("mock-google-token");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Google sign-in failed.");
    } finally {
      setIsGoogleLoading(false);
    }
  }

  return (
    <>
      <div className="space-y-3 pt-2">
        <div className="relative flex items-center justify-center">
          <div className="w-full border-t border-slate-700/60" />
          <span className="bg-[#0c1424] px-3 text-[11px] font-medium uppercase tracking-wider text-slate-400">
            Or continue with
          </span>
        </div>

        <div className="space-y-2">
          {/* If Real Google is configured, render official Google GSI Button */}
          {isRealGoogleConfigured ? (
            <div className="flex justify-center w-full min-h-[40px]">
              <div ref={googleBtnRef} className="w-full flex justify-center" />
            </div>
          ) : (
            /* Instant 1-click Google Sign-in for local dev */
            <button
              type="button"
              onClick={handleDevGoogleMockLogin}
              disabled={isGoogleLoading}
              className="w-full flex items-center justify-center gap-2 rounded border border-slate-300 bg-white px-4 py-2.5 text-xs font-semibold text-slate-800 hover:bg-slate-100 transition shadow-sm cursor-pointer"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
              <span>{isGoogleLoading ? "Signing in with Google..." : "Sign in with Google"}</span>
            </button>
          )}

          {/* GitHub Flow Button */}
          <button
            type="button"
            onClick={handleGithubButtonClick}
            disabled={isGithubLoading}
            className="w-full flex items-center justify-center gap-2 rounded border border-slate-300 bg-white px-4 py-2.5 text-xs font-semibold text-slate-800 hover:bg-slate-100 transition shadow-sm cursor-pointer"
          >
            <Github size={16} />
            <span>{isGithubLoading ? "Connecting GitHub..." : "Continue with GitHub"}</span>
          </button>
        </div>
      </div>

      {/* High-Tech GitHub Account Authentication Modal */}
      {showGithubModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-fade-in">
          <div className="relative w-full max-w-md rounded-2xl border border-emerald-500/30 bg-[#0c1424] p-6 shadow-2xl text-slate-100 space-y-5 animate-scale-in">
            {/* Modal Header */}
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-emerald-950/60 border border-emerald-500/40 text-emerald-400">
                  <Github size={22} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-100">Sign in with GitHub</h3>
                  <p className="text-xs text-slate-400">Connect account to access your repositories</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowGithubModal(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
              >
                <X size={18} />
              </button>
            </div>

            {/* Fast 1-Click Card: Ajaymallavali (Default Developer Account) */}
            <div className="rounded-xl border border-emerald-500/40 bg-gradient-to-br from-emerald-950/30 to-[#0a1322] p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <img
                    src="https://github.com/Ajaymallavali.png"
                    alt="Ajaymallavali"
                    className="w-10 h-10 rounded-full border-2 border-emerald-400/80 object-cover shadow-sm"
                    onError={(e) => {
                      (e.target as HTMLElement).style.display = "none";
                    }}
                  />
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-semibold text-slate-100">Ajay Mallavalli</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        Default
                      </span>
                    </div>
                    <p className="text-xs font-mono text-emerald-400">@Ajaymallavali</p>
                  </div>
                </div>
                <Sparkles size={16} className="text-emerald-400 animate-pulse" />
              </div>

              <p className="text-[11px] text-slate-400 leading-relaxed">
                One-click instant authentication: Syncs <span className="text-slate-200 font-medium">TREND-TECH-2</span> and personal repositories directly into your dashboard.
              </p>

              <button
                type="button"
                onClick={() => handleDirectGithubLogin("Ajaymallavali")}
                disabled={isGithubLoading}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 px-4 py-2.5 text-xs font-bold text-slate-950 shadow-md hover:from-emerald-400 hover:to-teal-400 active:scale-[0.98] transition cursor-pointer disabled:opacity-50"
              >
                {isGithubLoading ? (
                  <span>Authenticating & Loading Repositories...</span>
                ) : (
                  <>
                    <span>Sign in as @Ajaymallavali</span>
                    <ArrowRight size={14} />
                  </>
                )}
              </button>
            </div>

            {/* Custom GitHub Account Form */}
            <div className="space-y-3">
              <button
                type="button"
                onClick={() => setShowCustomFields(!showCustomFields)}
                className="text-xs text-emerald-400 hover:text-emerald-300 transition flex items-center gap-1.5 font-medium cursor-pointer"
              >
                <span>{showCustomFields ? "− Hide custom account fields" : "+ Sign in with a different GitHub username"}</span>
              </button>

              {showCustomFields && (
                <div className="space-y-3 pt-1 border-t border-slate-800">
                  <div>
                    <label className="block text-[11px] font-medium text-slate-300 mb-1">
                      GitHub Username
                    </label>
                    <div className="relative">
                      <UserIcon size={14} className="absolute left-3 top-2.5 text-emerald-400" />
                      <input
                        type="text"
                        value={customUsername}
                        onChange={(e) => setCustomUsername(e.target.value)}
                        placeholder="e.g. octocat"
                        className="w-full rounded-lg border border-[#1e2d42] bg-[#070b13] pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-slate-300 mb-1">
                      Personal Access Token (optional)
                    </label>
                    <div className="relative">
                      <Key size={14} className="absolute left-3 top-2.5 text-emerald-400" />
                      <input
                        type="password"
                        value={customToken}
                        onChange={(e) => setCustomToken(e.target.value)}
                        placeholder="ghp_... (optional for private repos)"
                        className="w-full rounded-lg border border-[#1e2d42] bg-[#070b13] pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
                      />
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleDirectGithubLogin(customUsername, customToken)}
                    disabled={isGithubLoading || !customUsername.trim()}
                    className="w-full flex items-center justify-center gap-2 rounded-lg border border-emerald-500/40 bg-emerald-950/40 px-4 py-2 text-xs font-semibold text-emerald-300 hover:bg-emerald-900/50 transition cursor-pointer disabled:opacity-40"
                  >
                    <span>Connect @{customUsername.trim() || "user"} & Load Repos</span>
                    <ArrowRight size={13} />
                  </button>
                </div>
              )}

              {/* Official OAuth Redirect Option if Configured */}
              {isOauthConfigured && oauthUrl && (
                <div className="pt-2 border-t border-slate-800">
                  <a
                    href={oauthUrl}
                    className="w-full flex items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-700 transition"
                  >
                    <Github size={14} />
                    <span>Authorize with GitHub OAuth</span>
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
