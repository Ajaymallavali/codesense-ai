import os
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_cors_origins() -> list[str]:
    defaults = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8050",
        "https://codesense-ai.pages.dev",
    ]
    env_origins = os.getenv("CORS_ORIGINS")
    if env_origins:
        for origin in env_origins.split(","):
            cleaned = origin.strip().rstrip("/")
            if cleaned and cleaned not in defaults:
                defaults.append(cleaned)
    return defaults


def _normalize_http_url(url: str | None, default: str) -> str:
    val = (url or default).strip().rstrip("/")
    if not val.startswith("http://") and not val.startswith("https://"):
        val = f"http://{val}"
    return val


class Settings(BaseSettings):
    app_name: str = "CodeSense FastAPI Backend"
    database_url: str = os.getenv("DATABASE_URL") or "postgresql://codesense:codesense@localhost:5432/codesense"
    ai_service_url: str = _normalize_http_url(os.getenv("AI_SERVICE_URL"), "http://localhost:8000")
    redis_url: str = os.getenv("REDIS_URL") or "redis://localhost:6379/0"
    jwt_secret: str = os.getenv("JWT_SECRET") or "local-dev-secret-change-before-production-please"
    jwt_expiration_minutes: int = 1440
    cors_origins: list[str] = _get_cors_origins()

    # OAuth & Webhook Settings
    github_client_id: str = os.getenv("GITHUB_CLIENT_ID") or "Ov23liC0emya5wo1KHtO"
    github_client_secret: str = os.getenv("GITHUB_CLIENT_SECRET") or ""
    github_redirect_uri: str = os.getenv("GITHUB_REDIRECT_URI") or "https://codesense-ai-ten-nu.vercel.app/"
    github_webhook_secret: str = os.getenv("GITHUB_WEBHOOK_SECRET") or ""
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID") or ""

    # Generative AI Model Configuration: Cloudflare Workers AI & Qwen
    llm_provider: str = os.getenv("LLM_PROVIDER") or "cloudflare"
    
    # Cloudflare Workers AI Configuration
    cloudflare_api_token: str = os.getenv("CLOUDFLARE_API_TOKEN") or os.getenv("CODESENSE_CLOUDFLARE_API_TOKEN") or ""
    cloudflare_account_id: str = os.getenv("CLOUDFLARE_ACCOUNT_ID") or os.getenv("CODESENSE_CLOUDFLARE_ACCOUNT_ID") or ""
    cloudflare_model: str = os.getenv("CLOUDFLARE_MODEL") or os.getenv("CODESENSE_CLOUDFLARE_MODEL") or "@cf/qwen/qwen2.5-coder-32b-instruct"
    cloudflare_timeout: int = int(os.getenv("CLOUDFLARE_TIMEOUT") or os.getenv("CODESENSE_CLOUDFLARE_TIMEOUT") or 120)
    cloudflare_max_retries: int = int(os.getenv("CLOUDFLARE_MAX_RETRIES") or os.getenv("CODESENSE_CLOUDFLARE_MAX_RETRIES") or 2)
    cloudflare_max_output_tokens: int = int(os.getenv("CLOUDFLARE_MAX_OUTPUT_TOKENS") or os.getenv("CODESENSE_CLOUDFLARE_MAX_OUTPUT_TOKENS") or 1500)

    # Qwen / DashScope Configuration
    qwen_model: str = os.getenv("QWEN_MODEL") or os.getenv("CODESENSE_QWEN_MODEL") or "Qwen/Qwen3-Coder-Next"
    qwen_base_url: str = os.getenv("QWEN_BASE_URL") or os.getenv("CODESENSE_QWEN_BASE_URL") or "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    qwen_api_key: str = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or os.getenv("CODESENSE_QWEN_API_KEY") or ""
    qwen_timeout: int = int(os.getenv("QWEN_TIMEOUT") or os.getenv("CODESENSE_QWEN_TIMEOUT") or 120)
    qwen_max_retries: int = int(os.getenv("QWEN_MAX_RETRIES") or os.getenv("CODESENSE_QWEN_MAX_RETRIES") or 2)
    qwen_max_output_tokens: int = int(os.getenv("QWEN_MAX_OUTPUT_TOKENS") or os.getenv("CODESENSE_QWEN_MAX_OUTPUT_TOKENS") or 1500)

    frontend_url: str = os.getenv("FRONTEND_URL") or "https://codesense-ai-ten-nu.vercel.app"
    environment: str = "development"

    model_config = SettingsConfigDict(env_prefix="CODESENSE_", env_file=".env", extra="ignore")


settings = Settings()
