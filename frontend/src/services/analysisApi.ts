import { request } from "./apiClient";
import { Analysis, Finding } from "../types";

export const analysisApi = {
  async getLatestAnalysis(repositoryId: string): Promise<Analysis | null> {
    return request<Analysis | null>(`/analysis/latest?repositoryId=${repositoryId}`);
  },

  async triggerAnalysis(repositoryId: string): Promise<Analysis> {
    return request<Analysis>(`/analysis/trigger?repositoryId=${repositoryId}`, {
      method: "POST",
    });
  },

  async getFindings(analysisId: string): Promise<Finding[]> {
    return request<Finding[]>(`/analysis/${analysisId}/findings`);
  },

  async getAnalysisHistory(repositoryId: string): Promise<Analysis[]> {
    return request<Analysis[]>(`/analysis/history?repositoryId=${repositoryId}`);
  },

  async getSampleAnalysis(): Promise<Record<string, unknown>> {
    return request<Record<string, unknown>>("/analysis/sample");
  },
};
