import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ai_client import ai_client
from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.analysis import router as analysis_router
from app.api.common import (
    analysis_response,
    auth_response,
    error_response,
    finding_response,
    repository_response,
    to_camel,
    user_response,
)
from app.api.reports import router as reports_router
from app.api.repositories import router as repositories_router
from app.api.users import router as users_router
from app.api.webhooks import router as webhooks_router
from app.api.organizations import router as organizations_router
from app.config import settings
from app.database import initialize_database
from app.jobs import check_redis_health

logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title=settings.app_name, version="0.2.0", root_path="", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return error_response(request, exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    field_errors: dict[str, str] = {}
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", []) if part != "body"]
        if location:
            field_errors[to_camel(location[-1])] = str(error.get("msg", "Invalid value"))
    return error_response(request, status.HTTP_400_BAD_REQUEST, "Please check the highlighted fields.", field_errors)


@app.get("/health")
@app.get("/api/health")
async def health() -> dict[str, Any]:
    ai_status = await ai_client.check_health()
    redis_status = check_redis_health()
    return {
        "service": "codesense-fastapi-backend",
        "status": "UP",
        "aiService": ai_status,
        "redis": redis_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Mount Modular Feature Routers
app.include_router(auth_router, prefix="/api/auth")
app.include_router(users_router, prefix="/api/users")
app.include_router(repositories_router, prefix="/api/repositories")
app.include_router(analysis_router, prefix="/api/analysis")
app.include_router(reports_router, prefix="/api/reports")
app.include_router(ai_router, prefix="/api/ai")
app.include_router(webhooks_router, prefix="/api/webhooks")
app.include_router(organizations_router, prefix="/api/organizations")

__all__ = [
    "app",
    "auth_response",
    "user_response",
    "repository_response",
    "analysis_response",
    "finding_response",
    "error_response",
    "to_camel",
]
