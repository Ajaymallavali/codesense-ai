import { request } from "./apiClient";
import { AuthResponse, User } from "../types";

export const authApi = {
  async register(form: { email: string; displayName: string; password: string }): Promise<AuthResponse> {
    return request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(form),
    });
  },

  async login(form: { email: string; password: string }): Promise<AuthResponse> {
    return request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(form),
    });
  },

  async googleAuth(credential: string): Promise<AuthResponse> {
    return request<AuthResponse>("/auth/google", {
      method: "POST",
      body: JSON.stringify({ credential }),
    });
  },

  async getMe(): Promise<User> {
    return request<User>("/auth/me");
  },

  async getGithubOAuthUrl(): Promise<{ configured: boolean; url: string; message?: string }> {
    return request<{ configured: boolean; url: string; message?: string }>("/auth/github/url");
  },

  async exchangeGithubCode(code: string): Promise<AuthResponse> {
    return request<AuthResponse>("/auth/github/exchange", {
      method: "POST",
      body: JSON.stringify({ code }),
    });
  },

  async updateProfile(payload: { displayName: string; githubUsername?: string; githubToken?: string }): Promise<User> {
    return request<User>("/users/profile", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  async updatePassword(payload: { oldPassword: string; newPassword: string }): Promise<{ message: string }> {
    return request<{ message: string }>("/users/password", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },
};
