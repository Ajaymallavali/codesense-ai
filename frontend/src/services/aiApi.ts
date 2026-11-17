import { request } from "./apiClient";
import { Citation, PrReviewData } from "../types";

export interface ChatResponse {
  response: string;
  answer?: string;
  citations?: Citation[];
  conversationId?: string;
  provider?: string;
}

export const aiApi = {
  async chat(
    repositoryId: string | undefined,
    query: string,
    conversationId?: string,
    messages?: { role: string; content?: string; text?: string }[]
  ): Promise<ChatResponse> {
    return request<ChatResponse>("/ai/chat", {
      method: "POST",
      body: JSON.stringify({
        repositoryId,
        query,
        conversationId,
        messages,
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

  async getConversation(conversationId: string): Promise<{
    conversationId: string;
    messages: { role: string; content: string; citations?: Citation[]; timestamp?: string }[];
  }> {
    return request<{
      conversationId: string;
      messages: { role: string; content: string; citations?: Citation[]; timestamp?: string }[];
    }>(`/ai/conversations/${conversationId}`, {
      method: "GET",
    });
  },

  async getLatestConversation(repositoryId: string): Promise<{
    conversationId: string | null;
    messages: { role: string; content: string; citations?: Citation[]; timestamp?: string }[];
  }> {
    return request<{
      conversationId: string | null;
      messages: { role: string; content: string; citations?: Citation[]; timestamp?: string }[];
    }>(`/ai/conversations/latest?repositoryId=${encodeURIComponent(repositoryId)}`, {
      method: "GET",
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
