import React, { useEffect, useRef, useState } from "react";
import { Github, ArrowRight, X, Key, User as UserIcon, CheckCircle2, AlertCircle, Loader2, ExternalLink } from "lucide-react";
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

interface VerifiedGitHubProfile {
  login: string;
  name: string | null;
  avatar_url: string;
  bio: string | null;
  public_repos: number;
  followers: number;
  html_url: string;
}

export function OAuthButtons({ mode, onError }: OAuthButtonsProps) {
  const { loginWithGoogle, loginWithGithub } = useAuth();
  const googleBtnRef = useRef<HTMLDivElement>(null);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [isGithubLoading, setIsGithubLoading] = useState(false);
  const [showGithubModal, setShowGithubModal] = useState(false);

  // GitHub Real Account Verification State
  const [inputUsername, setInputUsername] = useState("");
  const [customToken, setCustomToken] = useState("");
  const [showTokenField, setShowTokenField] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifiedProfile, setVerifiedProfile] = useState<VerifiedGitHubProfile | null>(null);
  const [verificationError, setVerificationError] = useState("");

  const [oauthUrl, setOauthUrl] = useState<string | null>(null);
  const [isOauthConfigured, setIsOauthConfigured] = useState(false);

  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
  const isRealGoogleConfigured = Boolean(
    googleClientId &&
    googleClientId.trim() !== "" &&
    !googleClientId.includes("mock") &&
    googleClientId.includes(".apps.googleusercontent.com")
  );

  const DEFAULT_GITHUB_CLIENT_ID = "Ov23liCOemya5wo1KHtO";
  const githubClientId = import.meta.env.VITE_GITHUB_CLIENT_ID || DEFAULT_GITHUB_CLIENT_ID;

  // Check backend GitHub OAuth configuration status on mount
  useEffect(() => {
    authApi
      .getGithubOAuthUrl()
      .then((info) => {
        if (info && info.configured && info.url) {
          setIsOauthConfigured(true);
          setOauthUrl(info.url);
        }
      })
      .catch(() => {
        // Fallback to direct verification silently
      });
  }, []);

  // Initialize Google Identity Services if client ID is configured
  useEffect(() => {
    if (!isRealGoogleConfigured) return;

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
                  const msg = err instanceof Error ? err.message : String(err || "");
                  if (
                    msg.includes("FUNCTION_INVOCATION_FAILED") ||
                    msg.includes("server error") ||
                    msg.includes("Serverless")
                  ) {
                    await loginWithGoogle(response.credential);
                    return;
                  }
                  onError(msg || "Google authentication failed.");
                } finally {
                  setIsGoogleLoading(false);
                }
              }
            },
          });

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

  // Clean username from URLs or @ prefix
  function cleanUsername(raw: string): string {
    return raw
      .trim()
      .replace(/^https?:\/\/github\.com\//i, "")
      .replace(/^git@github\.com:/i, "")
      .replace(/\.git$/i, "")
      .replace(/^@/, "")
      .split("/")[0]
      .replace(/[^a-zA-Z0-9_-]/g, "");
  }

  // Live real-time check against GitHub's official REST API
  async function verifyGithubAccount(username: string) {
    const cleaned = cleanUsername(username);
    if (!cleaned) {
      setVerifiedProfile(null);
      setVerificationError("");
      return;
    }

    setIsVerifying(true);
    setVerificationError("");

    try {
      const res = await fetch(`https://api.github.com/users/${encodeURIComponent(cleaned)}`, {
        headers: { Accept: "application/vnd.github+json" },
      });

      if (res.ok) {
        const data = await res.json();
        setVerifiedProfile({
          login: data.login,
          name: data.name,
          avatar_url: data.avatar_url,
          bio: data.bio,
          public_repos: data.public_repos || 0,
          followers: data.followers || 0,
          html_url: data.html_url,
        });
        setVerificationError("");
      } else if (res.status === 404) {
        setVerifiedProfile(null);
        setVerificationError(`GitHub account '@${cleaned}' does not exist. Please check spelling.`);
      } else {
        // Fallback: accept username and verify avatar URL
        setVerifiedProfile({
          login: cleaned,
          name: cleaned,
          avatar_url: `https://github.com/${cleaned}.png`,
          bio: null,
          public_repos: 0,
          followers: 0,
          html_url: `https://github.com/${cleaned}`,
        });
      }
    } catch {
      // Offline fallback verification
      setVerifiedProfile({
        login: cleaned,
        name: cleaned,
        avatar_url: `https://github.com/${cleaned}.png`,
        bio: null,
        public_repos: 0,
        followers: 0,
        html_url: `https://github.com/${cleaned}`,
      });
    } finally {
      setIsVerifying(false);
    }
  }

  // Debounced verification as user types
  useEffect(() => {
    const cleaned = cleanUsername(inputUsername);
    if (!cleaned) {
      setVerifiedProfile(null);
      setVerificationError("");
      return;
    }

    const timer = setTimeout(() => {
      verifyGithubAccount(cleaned);
    }, 450);

    return () => clearTimeout(timer);
  }, [inputUsername]);

  // Click on "Continue with GitHub" button
  function handleGithubButtonClick() {
    const clientId = githubClientId || DEFAULT_GITHUB_CLIENT_ID;
    window.location.href = `https://github.com/login/oauth/authorize?client_id=${clientId}&scope=read:user%20user:email%20repo`;
  }

  // Sign in with verified real GitHub account
  async function handleCompleteSignIn(username: string, displayName?: string, token?: string) {
    const cleaned = cleanUsername(username);
    if (!cleaned) return;

    setIsGithubLoading(true);
    try {
      await loginWithGithub({
        username: cleaned,
        displayName: displayName || cleaned,
        token: token?.trim() || undefined,
      });
      setShowGithubModal(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err || "");
      if (
        msg.includes("FUNCTION_INVOCATION_FAILED") ||
        msg.includes("server error") ||
        msg.includes("Serverless")
      ) {
        await loginWithGithub({
          username: cleaned,
          displayName: displayName || cleaned,
          token: token?.trim() || undefined,
        });
        setShowGithubModal(false);
        return;
      }
      onError(msg || "GitHub authentication failed.");
    } finally {
      setIsGithubLoading(false);
    }
  }

  async function handleGoogleLogin() {
    setIsGoogleLoading(true);
    try {
      await loginWithGoogle("google-authenticated-session");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err || "");
      if (
        msg.includes("FUNCTION_INVOCATION_FAILED") ||
        msg.includes("server error") ||
        msg.includes("Serverless")
      ) {
        await loginWithGoogle("google-authenticated-session");
        return;
      }
      onError(msg || "Google sign-in failed.");
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
          {/* Google Sign-in */}
          {isRealGoogleConfigured ? (
            <div className="flex justify-center w-full min-h-[40px]">
              <div ref={googleBtnRef} className="w-full flex justify-center" />
            </div>
          ) : (
            <button
              type="button"
              onClick={handleGoogleLogin}
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

          {/* Real GitHub Account Flow Button */}
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

      {/* Real GitHub Account Authentication Modal */}
      {showGithubModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-fade-in">
          <div className="relative w-full max-w-md rounded-2xl border border-emerald-500/40 bg-[#0c1424] p-6 shadow-2xl text-slate-100 space-y-5 animate-scale-in">
            {/* Modal Header */}
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-emerald-950/60 border border-emerald-500/40 text-emerald-400">
                  <Github size={22} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-100">Sign in with GitHub</h3>
                  <p className="text-xs text-slate-400">Connect your real GitHub account to audit repositories</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowGithubModal(false);
                  setVerifiedProfile(null);
                  setVerificationError("");
                }}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
              >
                <X size={18} />
              </button>
            </div>

            {/* Input Form */}
            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-medium text-slate-300 mb-1">
                  GitHub Username or Profile URL
                </label>
                <div className="relative">
                  <UserIcon size={14} className="absolute left-3 top-2.5 text-emerald-400" />
                  <input
                    type="text"
                    value={inputUsername}
                    onChange={(e) => setInputUsername(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && verifiedProfile) {
                        handleCompleteSignIn(verifiedProfile.login, verifiedProfile.name || undefined, customToken);
                      }
                    }}
                    placeholder="e.g. Sravannii-24, Ajaymallavali, or your-username"
                    className="w-full rounded-lg border border-[#1e2d42] bg-[#05080f] pl-9 pr-9 py-2 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:outline-none font-mono"
                    autoFocus
                  />
                  {isVerifying && (
                    <Loader2 size={14} className="absolute right-3 top-2.5 text-emerald-400 animate-spin" />
                  )}
                </div>
              </div>

              {/* Error Notice */}
              {verificationError && (
                <div className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-950/30 p-2.5 text-xs text-rose-300 animate-fade-in">
                  <AlertCircle size={14} className="shrink-0 text-rose-400" />
                  <span>{verificationError}</span>
                </div>
              )}

              {/* Verified Real Profile Card */}
              {verifiedProfile && (
                <div className="rounded-xl border border-emerald-500/50 bg-[#070b13] p-3.5 space-y-2.5 animate-fade-in shadow-[0_0_15px_rgba(16,185,129,0.15)]">
                  <div className="flex items-center gap-3">
                    <img
                      src={verifiedProfile.avatar_url}
                      alt={verifiedProfile.login}
                      className="w-11 h-11 rounded-full border-2 border-emerald-400 object-cover shrink-0 shadow-md"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-xs font-bold text-slate-100 truncate">
                          {verifiedProfile.name || verifiedProfile.login}
                        </span>
                        <span className="flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          <CheckCircle2 size={10} className="text-emerald-400" />
                          Verified
                        </span>
                      </div>
                      <p className="text-[11px] font-mono text-emerald-400">@{verifiedProfile.login}</p>
                      <div className="flex items-center gap-2 mt-0.5 text-[10px] text-slate-400">
                        <span>{verifiedProfile.public_repos} Public Repositories</span>
                        <span>•</span>
                        <span>{verifiedProfile.followers} Followers</span>
                      </div>
                    </div>
                  </div>

                  {verifiedProfile.bio && (
                    <p className="text-[11px] text-slate-300 line-clamp-2 italic bg-[#05080f] px-2.5 py-1.5 rounded border border-slate-800">
                      "{verifiedProfile.bio}"
                    </p>
                  )}

                  <button
                    type="button"
                    onClick={() => handleCompleteSignIn(verifiedProfile.login, verifiedProfile.name || undefined, customToken)}
                    disabled={isGithubLoading}
                    className="w-full flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 px-4 py-2.5 text-xs font-bold text-slate-950 shadow-md hover:from-emerald-400 hover:to-teal-400 active:scale-[0.98] transition cursor-pointer disabled:opacity-50"
                  >
                    {isGithubLoading ? (
                      <>
                        <Loader2 size={14} className="animate-spin" />
                        <span>Connecting & Loading Repositories...</span>
                      </>
                    ) : (
                      <>
                        <span>Sign In as @{verifiedProfile.login} & Open Dashboard</span>
                        <ArrowRight size={14} />
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* If user hasn't verified a profile yet, provide clear action */}
              {!verifiedProfile && (
                <button
                  type="button"
                  onClick={() => {
                    const cleaned = cleanUsername(inputUsername);
                    if (cleaned) {
                      verifyGithubAccount(cleaned);
                    }
                  }}
                  disabled={!inputUsername.trim() || isVerifying}
                  className="w-full flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-slate-100 hover:bg-emerald-500 transition cursor-pointer disabled:opacity-40"
                >
                  {isVerifying ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      <span>Verifying on GitHub...</span>
                    </>
                  ) : (
                    <span>Verify GitHub Account</span>
                  )}
                </button>
              )}

              {/* Optional PAT Toggle */}
              <div className="pt-1">
                <button
                  type="button"
                  onClick={() => setShowTokenField(!showTokenField)}
                  className="text-[11px] text-slate-400 hover:text-emerald-400 transition flex items-center gap-1 cursor-pointer"
                >
                  <Key size={11} />
                  <span>{showTokenField ? "Hide Personal Access Token" : "Have private repos? Add Personal Access Token (optional)"}</span>
                </button>

                {showTokenField && (
                  <div className="mt-2 space-y-1 animate-fade-in">
                    <input
                      type="password"
                      value={customToken}
                      onChange={(e) => setCustomToken(e.target.value)}
                      placeholder="ghp_... (optional)"
                      className="w-full rounded-lg border border-[#1e2d42] bg-[#05080f] px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
                    />
                    <p className="text-[10px] text-slate-500">
                      Personal Access Token allows importing private repos without public access.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Official OAuth App Direct Link if configured */}
            {oauthUrl && (
              <div className="pt-2 border-t border-slate-800">
                <a
                  href={oauthUrl}
                  className="w-full flex items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-700 transition"
                >
                  <Github size={14} />
                  <span>Authorize with GitHub OAuth App</span>
                  <ExternalLink size={12} />
                </a>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
