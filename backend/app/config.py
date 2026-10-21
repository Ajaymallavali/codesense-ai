import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CodeSense FastAPI Backend"
    database_url: str = os.getenv("DATABASE_URL") or "postgresql://codesense:codesense@localhost:5432/codesense"
    ai_service_url: str = os.getenv("AI_SERVICE_URL") or "http://localhost:8000"
    redis_url: str = os.getenv("REDIS_URL") or "redis://localhost:6379/0"
    jwt_secret: str = os.getenv("JWT_SECRET") or "local-dev-secret-change-before-production-please"
    jwt_expiration_minutes: int = 1440
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # OAuth, AI & Webhook Settings
    github_client_id: str = os.getenv("GITHUB_CLIENT_ID") or ""
    github_client_secret: str = os.getenv("GITHUB_CLIENT_SECRET") or ""
    github_redirect_uri: str = "http://localhost:8050/api/auth/github/callback"
    github_webhook_secret: str = os.getenv("GITHUB_WEBHOOK_SECRET") or ""
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID") or ""
    gemini_api_key: str = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    frontend_url: str = "http://localhost:5173"
    environment: str = "development"

    model_config = SettingsConfigDict(env_prefix="CODESENSE_", env_file=".env", extra="ignore")


settings = Settings()
