import { request } from "./apiClient";
import { PrReviewData } from "../types";

export const aiApi = {
  async chat(repositoryId: string | undefined, query: string): Promise<{ response: string; answer?: string }> {
    return request<{ response: string; answer?: string }>("/ai/chat", {
      method: "POST",
      body: JSON.stringify({
        repositoryId,
        query,
      }),
    });
  },

  async explain(findingId?: string, code?: string): Promise<{ explanation: string; suggestion: string }> {
    return request<{ explanation: string; suggestion: string }>("/ai/explain", {
      method: "POST",
      body: JSON.stringify({
        findingId,
        code,
      }),
    });
  },

  async reviewPr(payload: {
    repositoryId?: string;
    repositoryUrl?: string;
    branch?: string;
    baseBranch?: string;
    prTitle?: string;
    prDescription?: string;
    diff?: string;
  }): Promise<PrReviewData> {
    return request<PrReviewData>("/ai/review/pr", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
