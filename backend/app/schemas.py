from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    displayName: str
    githubUsername: str | None = None
    createdAt: datetime


class RegisterRequest(BaseModel):
    email: EmailStr
    displayName: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=8, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class GoogleAuthRequest(BaseModel):
    credential: str = Field(min_length=1)


class GitHubCallbackRequest(BaseModel):
    code: str = Field(min_length=1)


class AuthResponse(BaseModel):
    token: str
    tokenType: str = "Bearer"
    user: UserResponse


class UpdateProfileRequest(BaseModel):
    displayName: str = Field(min_length=2, max_length=80)
    githubToken: str | None = Field(default=None, max_length=500)
    githubUsername: str | None = Field(default=None, max_length=255)


class UpdatePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str = Field(min_length=8, max_length=120)


class ImportRepositoryRequest(BaseModel):
    name: str
    fullName: str | None = None
    defaultBranch: str = "main"
    language: str | None = None
    githubId: int | None = None


class RepositoryResponse(BaseModel):
    id: UUID
    name: str
    fullName: str
    defaultBranch: str
    language: str | None = None
    importedAt: datetime


class FindingResponse(BaseModel):
    id: UUID
    category: str
    severity: str
    filePath: str
    title: str
    suggestion: str | None = None
    lineNumber: int | None = None


class AnalysisResponse(BaseModel):
    id: UUID
    repositoryId: UUID
    branch: str
    maintainabilityScore: int | None = 0
    technicalDebtHours: int | None = 0
    status: str
    progress: int | None = 0
    errorMessage: str | None = None
    startedAt: datetime
    completedAt: datetime | None = None


class TriggerAnalysisRequest(BaseModel):
    repositoryId: UUID | None = None


class AiChatRequest(BaseModel):
    query: str | None = None
    message: str | None = None
    repositoryId: UUID | None = None


class AiExplainRequest(BaseModel):
    findingId: UUID | None = None
    code: str | None = None
    language: str | None = None


class PrInlineComment(BaseModel):
    filePath: str
    lineNumber: int | None = None
    severity: str
    comment: str
    suggestedPatch: str | None = None


class PrReviewRequest(BaseModel):
    repositoryId: UUID | None = None
    repositoryUrl: str | None = None
    branch: str = "main"
    baseBranch: str = "main"
    prTitle: str | None = None
    prDescription: str | None = None
    diff: str | None = None


class PrReviewResponse(BaseModel):
    summary: str
    verdict: str  # APPROVE, REQUEST_CHANGES, COMMENT
    riskLevel: str  # Low, Medium, High, Critical
    inlineComments: list[PrInlineComment] = []
    suggestedImprovements: list[str] = []
