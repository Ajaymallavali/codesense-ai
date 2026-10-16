export type AuthMode = "login" | "register" | "forgot";

export type User = {
  id: string;
  email: string;
  displayName: string;
  githubUsername?: string | null;
  githubToken?: string | null;
  createdAt: string;
};

export type AuthResponse = {
  token: string;
  tokenType: string;
  user: User;
};

export type ApiErrorResponse = {
  status?: number;
  error?: string;
  message?: string;
  fieldErrors?: Record<string, string>;
};

export type AuthFormErrors = {
  displayName?: string;
  email?: string;
  password?: string;
};

export type Repository = {
  id: string;
  name: string;
  fullName: string;
  defaultBranch: string;
  language?: string | null;
  importedAt: string;
};

export type RemoteRepository = {
  id: number;
  name: string;
  fullName?: string;
  full_name?: string;
  language?: string | null;
  defaultBranch?: string;
  default_branch?: string;
  private?: boolean;
  description?: string | null;
};

export type Finding = {
  id: string;
  category: string;
  severity: "Critical" | "High" | "Medium" | "Low" | string;
  filePath: string;
  title: string;
  suggestion?: string | null;
  lineNumber?: number | null;
};

export type Analysis = {
  id: string;
  repositoryId: string;
  branch: string;
  maintainabilityScore: number;
  technicalDebtHours: number;
  status: "PENDING" | "SCANNING" | "RUNNING" | "COMPLETED" | "FAILED" | string;
  progress: number;
  errorMessage?: string | null;
  startedAt: string;
  completedAt?: string | null;
};

export type PrInlineComment = {
  filePath: string;
  lineNumber?: number | null;
  severity: string;
  comment: string;
  suggestedPatch?: string | null;
};

export type PrReviewData = {
  summary: string;
  verdict: "APPROVE" | "REQUEST_CHANGES" | "COMMENT" | string;
  riskLevel: "Low" | "Medium" | "High" | "Critical" | string;
  inlineComments: PrInlineComment[];
  suggestedImprovements: string[];
};

export type ReportSummary = {
  repository: string;
  branch: string;
  language: string;
  analysisId?: string | null;
  completedAt: string;
  maintainabilityScore: number;
  technicalDebtHours: number;
  findingsCount: number;
  findingsByCategory: Record<string, number>;
  findings: Finding[];
};

export type ChatMessage = {
  role: "user" | "assistant";
  text: string;
};
