import React, { useEffect, useRef, useState } from "react";
import { Github } from "lucide-react";
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
  const { loginWithGoogle } = useAuth();
  const googleBtnRef = useRef<HTMLDivElement>(null);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [isGithubLoading, setIsGithubLoading] = useState(false);
  const [gsiInitialized, setGsiInitialized] = useState(false);

  const googleClientId =
    import.meta.env.VITE_GOOGLE_CLIENT_ID ||
    "1234567890-mockclientid.apps.googleusercontent.com";

  // Load Google Identity Services (GSI) script dynamically
  useEffect(() => {
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
          setGsiInitialized(true);
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
  }, [googleClientId, mode]);

  // Handle GitHub OAuth Redirect
  async function handleGithubLogin() {
    setIsGithubLoading(true);
    try {
      const info = await authApi.getGithubOAuthUrl();
      if (info.url) {
        window.location.href = info.url;
      } else {
        onError(info.message || "GitHub OAuth is not configured on the server.");
      }
    } catch (err) {
      onError(err instanceof Error ? err.message : "GitHub OAuth failed to initialize.");
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
    <div className="space-y-3 pt-2">
      <div className="relative flex items-center justify-center">
        <div className="w-full border-t border-slate-200" />
        <span className="bg-white px-3 text-[11px] font-medium uppercase tracking-wider text-slate-400">
          Or continue with
        </span>
      </div>

      <div className="space-y-2">
        {/* Real Google GSI Container */}
        <div className="flex justify-center w-full min-h-[40px]">
          <div ref={googleBtnRef} className="w-full flex justify-center" />
        </div>

        {/* Fallback button if GSI is loading or blocked by adblock */}
        {!gsiInitialized && (
          <button
            type="button"
            onClick={handleDevGoogleMockLogin}
            disabled={isGoogleLoading}
            className="w-full flex items-center justify-center gap-2 rounded border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition shadow-sm"
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

        {/* GitHub OAuth Flow Button */}
        <button
          type="button"
          onClick={handleGithubLogin}
          disabled={isGithubLoading}
          className="w-full flex items-center justify-center gap-2 rounded border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition shadow-sm"
        >
          <Github size={15} />
          <span>{isGithubLoading ? "Connecting GitHub..." : "Continue with GitHub"}</span>
        </button>
      </div>
    </div>
  );
}
