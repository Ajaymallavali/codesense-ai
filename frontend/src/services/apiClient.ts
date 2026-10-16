import { ApiErrorResponse } from "../types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8050/api";
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
      message = text || message;
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
  return res.text() as unknown as Promise<T>;
}
