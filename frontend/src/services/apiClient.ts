import { ApiErrorResponse } from "../types";

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL;
export const API_BASE_URL = (
  configuredBaseUrl && configuredBaseUrl.trim() !== ""
    ? configuredBaseUrl.trim()
    : (typeof window !== "undefined"
        ? (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
            ? "http://localhost:8050/api"
            : `${window.location.origin}/api`)
        : "http://localhost:8050/api")
).replace(/\/+$/, "");
export const AUTH_STORAGE_KEY = "codesense.auth";

export class ApiError extends Error {
  status: number;
  fieldErrors: Record<string, string>;

  constructor(message: string, status: number = 400, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

export function getStoredToken(): string | null {
  const raw = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    return parsed.token || null;
  } catch {
    return null;
  }
}

export function setStoredToken(token: string): void {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ token }));
}

export function clearStoredToken(): void {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

export async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  customToken?: string | null
): Promise<T> {
  const token = customToken !== undefined ? customToken : getStoredToken();
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`;

  let res: Response;
  try {
    res = await fetch(url, { ...options, headers });
  } catch (err) {
    throw new ApiError("Unable to connect to CodeSense server. Ensure backend is running.", 0);
  }

  if (!res.ok) {
    const text = await res.text();
    let message = `Request failed with status ${res.status}`;
    let fieldErrors: Record<string, string> = {};

    try {
      const json: ApiErrorResponse = JSON.parse(text);
      message = json.message || json.error || message;
      if (json.fieldErrors) {
        fieldErrors = json.fieldErrors;
      }
    } catch {
      const lowerText = (text || "").toLowerCase();
      if (
        lowerText.includes("function_invocation_failed") ||
        lowerText.includes("server error has occurred") ||
        res.status >= 500
      ) {
        message = "Serverless service temporarily cooling down. Resilient offline session activated.";
      } else {
        message = text || message;
      }
    }

    if (res.status === 401) {
      clearStoredToken();
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("codesense:unauthorized"));
      }
    }

    throw new ApiError(message, res.status, fieldErrors);
  }

  // Handle empty or text responses
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return res.json() as Promise<T>;
  }

  const text = await res.text();

  // If the server returned HTML (e.g. SPA index.html fallback for missing API endpoints on static hosting)
  if (
    contentType.includes("text/html") ||
    text.trim().toLowerCase().startsWith("<!doctype") ||
    text.trim().toLowerCase().startsWith("<html")
  ) {
    throw new ApiError(
      `API endpoint returned HTML document instead of JSON. Backend service is not running or route not found (${url}).`,
      404
    );
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    return text as unknown as T;
  }
}
