import { request } from "./apiClient";
import { RemoteRepository, Repository } from "../types";

export const githubApi = {
  async getImportedRepositories(): Promise<Repository[]> {
    return request<Repository[]>("/repositories");
  },

  async getRemoteRepositories(username?: string): Promise<RemoteRepository[]> {
    const query = username ? `?username=${encodeURIComponent(username)}` : "";
    return request<RemoteRepository[]>(`/repositories/github${query}`);
  },

  async getBranches(fullName: string): Promise<string[]> {
    return request<string[]>(`/repositories/github/branches?fullName=${encodeURIComponent(fullName)}`);
  },

  async getRepositoryDetails(fullName: string): Promise<RemoteRepository> {
    return request<RemoteRepository>(`/repositories/github/details?fullName=${encodeURIComponent(fullName)}`);
  },

  async importRepository(payload: {
    name: string;
    fullName?: string;
    defaultBranch?: string;
    language?: string | null;
    githubId?: number | null;
  }): Promise<Repository> {
    return request<Repository>("/repositories/import", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
