from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CodeSense FastAPI Backend"
    database_url: str = "postgresql://codesense:codesense@localhost:5432/codesense"
    ai_service_url: str = "http://localhost:8000"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "local-dev-secret-change-before-production-please"
    jwt_expiration_minutes: int = 1440
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # OAuth Settings
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8050/api/auth/github/callback"
    google_client_id: str = ""
    frontend_url: str = "http://localhost:5173"
    environment: str = "development"

    model_config = SettingsConfigDict(env_prefix="CODESENSE_", env_file=".env", extra="ignore")


settings = Settings()
