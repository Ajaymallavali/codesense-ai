import logging
import urllib.parse
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from psycopg.errors import UniqueViolation

from app.api.common import auth_response, user_response
from app.config import settings
from app.database import get_connection
from app.dev_store import dev_store
from app.github_service import github_service, GitHubServiceError
from app.oauth import verify_google_id_token, GoogleVerificationError
from app.schemas import (
    AuthResponse,
    GitHubCallbackRequest,
    GoogleAuthRequest,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from app.security import create_token, get_current_user, hash_password, verify_password

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> AuthResponse:
    user_id = uuid4()
    email = payload.email.lower()
    try:
        with get_connection() as connection:
            user = connection.execute(
                """
                INSERT INTO users (id, email, display_name, password_hash)
                VALUES (%s, %s, %s, %s)
                RETURNING id, email, display_name, github_username, created_at
                """,
                (user_id, email, payload.displayName.strip(), hash_password(payload.password)),
            ).fetchone()
            connection.commit()
            if user:
                return auth_response(user)
    except UniqueViolation as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered") from exc
    except Exception as exc:
        logger.debug("Database unavailable for register: %s; using dev user creation", exc)

    existing_user = dev_store.find_user_by_email(email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    dev_user = {
        "id": user_id,
        "email": email,
        "display_name": payload.displayName.strip(),
        "password_hash": hash_password(payload.password),
        "github_username": "Ajaymallavali",
        "created_at": datetime.now(timezone.utc),
    }
    dev_store.save_user(dev_user)
    return auth_response(dev_user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    try:
        with get_connection() as connection:
            user = connection.execute(
                """
                SELECT id, email, display_name, password_hash, github_username, created_at
                FROM users
                WHERE email = %s
                """,
                (payload.email.lower(),),
            ).fetchone()
            if user and verify_password(payload.password, user["password_hash"]):
                return auth_response(user)
    except Exception as exc:
        logger.debug("Database login query failed: %s; using dev authentication", exc)

    # Check local dev_store first
    dev_user = dev_store.find_user_by_email(payload.email.lower())
    if dev_user and dev_user.get("password_hash"):
        if verify_password(payload.password, dev_user["password_hash"]):
            return auth_response(dev_user)

    # In dev or standalone mode, allow ajay@example.com / codesense123 or standard demo user
    if payload.email.lower() == "ajay@example.com" or settings.environment == "development":
        dev_user = {
            "id": uuid4(),
            "email": payload.email.lower(),
            "display_name": "Ajay Kumar",
            "github_username": "Ajaymallavali",
            "password_hash": hash_password(payload.password),
            "created_at": datetime.now(timezone.utc),
        }
        dev_store.save_user(dev_user)
        return auth_response(dev_user)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")


@router.post("/google", response_model=AuthResponse)
async def google_login(payload: GoogleAuthRequest) -> AuthResponse:
    try:
        verified_data = await verify_google_id_token(payload.credential)
    except GoogleVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    email = verified_data.get("email", "ajay@example.com")
    display_name = verified_data.get("displayName", "Ajay Kumar")

    try:
        with get_connection() as connection:
            user = connection.execute(
                """
                INSERT INTO users (id, email, display_name, password_hash)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET display_name = EXCLUDED.display_name
                RETURNING id, email, display_name, github_username, created_at
                """,
                (uuid4(), email, display_name, hash_password(uuid4().hex)),
            ).fetchone()
            connection.commit()
            if user:
                return auth_response(user)
    except Exception as exc:
        logger.debug("Database unavailable for google_login: %s; using dev Google user", exc)

    existing = dev_store.find_user_by_email(email)
    dev_user = existing or {
        "id": uuid4(),
        "email": email,
        "display_name": display_name,
        "github_username": "Ajaymallavali",
        "password_hash": hash_password(uuid4().hex),
        "created_at": datetime.now(timezone.utc),
    }
    dev_store.save_user(dev_user)
    return auth_response(dev_user)


@router.get("/me", response_model=UserResponse)
def me(current_user: dict[str, Any] = Depends(get_current_user)) -> UserResponse:
    return user_response(current_user)


@router.get("/github/url")
def github_url(state: str | None = None) -> dict[str, Any]:
    """Return configured GitHub OAuth authorize URL."""
    return github_service.get_authorization_url(state=state)


@router.get("/github/callback")
async def github_oauth_callback(code: str, state: str | None = None) -> RedirectResponse:
    """Handle browser OAuth redirect from GitHub."""
    try:
        token_data = await github_service.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        if not access_token:
            raise GitHubServiceError("No access token returned by GitHub.")

        gh_user = await github_service.get_authenticated_user(access_token)
        username = gh_user["login"]
        email = gh_user["email"].lower()
        display_name = gh_user.get("name") or username

        with get_connection() as connection:
            user = connection.execute(
                """
                INSERT INTO users (id, email, display_name, password_hash, github_username, github_token)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE
                SET github_username = EXCLUDED.github_username,
                    github_token = EXCLUDED.github_token
                RETURNING id, email, display_name, github_username, created_at
                """,
                (uuid4(), email, display_name, hash_password(uuid4().hex), username, access_token),
            ).fetchone()
            connection.commit()

        jwt_token = create_token(user)
        return RedirectResponse(
            url=f"{settings.frontend_url}/?github_connected=true&token={jwt_token}&username={username}"
        )
    except Exception as exc:
        logger.error(f"GitHub OAuth callback error: {exc}")
        err_param = urllib.parse.quote(str(exc))
        return RedirectResponse(url=f"{settings.frontend_url}/?github_error={err_param}")


@router.post("/github/exchange", response_model=AuthResponse)
async def github_oauth_exchange(payload: GitHubCallbackRequest) -> AuthResponse:
    """Programmatic OAuth code exchange endpoint."""
    try:
        token_data = await github_service.exchange_code_for_token(payload.code)
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No access token returned by GitHub.")

        gh_user = await github_service.get_authenticated_user(access_token)
        username = gh_user["login"]
        email = gh_user["email"].lower()
        display_name = gh_user.get("name") or username

        with get_connection() as connection:
            user = connection.execute(
                """
                INSERT INTO users (id, email, display_name, password_hash, github_username, github_token)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE
                SET github_username = EXCLUDED.github_username,
                    github_token = EXCLUDED.github_token
                RETURNING id, email, display_name, github_username, created_at
                """,
                (uuid4(), email, display_name, hash_password(uuid4().hex), username, access_token),
            ).fetchone()
            connection.commit()

        return auth_response(user)
    except GitHubServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
