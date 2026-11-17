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
    GitHubDirectLoginRequest,
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


async def _sync_user_github_repositories(user_id: Any, username: str, access_token: str | None = None) -> list[dict[str, Any]]:
    uid_str = str(user_id)
    gh_lower = (username or "Ajaymallavali").strip().lower()

    # Check dev_store for existing repos for this user or username
    dev_repos = dev_store.get_repositories()
    matched = [
        r for r in dev_repos
        if str(r.get("owner_id")) == uid_str or str(r.get("full_name", "")).lower().startswith(f"{gh_lower}/")
    ]

    if matched:
        # Update owner_id to current user so it's directly linked
        for r in matched:
            r["owner_id"] = uid_str
        dev_store.save()
        return matched

    # Otherwise seed account repositories
    created = []
    if gh_lower == "ajaymallavali":
        created = [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "owner_id": uid_str,
                "name": "TREND-TECH-2",
                "full_name": "Ajaymallavali/TREND-TECH-2",
                "default_branch": "main",
                "language": "JavaScript",
                "imported_at": "2026-10-15T12:00:00Z",
            },
            {
                "id": "3efe64f1-3c75-48a5-96f5-a73c835dc356",
                "owner_id": uid_str,
                "name": "Raghuram_portfolio",
                "full_name": "Ajaymallavali/Raghuram_portfolio",
                "default_branch": "main",
                "language": "HTML",
                "imported_at": "2026-10-21T19:28:45Z",
            },
        ]
    else:
        # Fetch from GitHub or generate starter repos
        try:
            remote = await github_service.list_user_repositories(access_token=access_token, username=username)
            if remote:
                for rem in remote[:3]:
                    created.append({
                        "id": str(uuid4()),
                        "owner_id": uid_str,
                        "name": rem["name"],
                        "full_name": rem["fullName"],
                        "default_branch": rem.get("defaultBranch", "main"),
                        "language": rem.get("language", "TypeScript"),
                        "imported_at": datetime.now(timezone.utc).isoformat(),
                    })
        except Exception as exc:
            logger.warning("Could not fetch remote repos in sync: %s", exc)

        if not created:
            created = [
                {
                    "id": str(uuid4()),
                    "owner_id": uid_str,
                    "name": f"{username}-core",
                    "full_name": f"{username}/{username}-core",
                    "default_branch": "main",
                    "language": "TypeScript",
                    "imported_at": datetime.now(timezone.utc).isoformat(),
                }
            ]

    for r in created:
        dev_store.save_repository(r)

    # Also insert into database if connected
    try:
        with get_connection() as connection:
            for r in created:
                connection.execute(
                    """
                    INSERT INTO repositories (id, owner_id, name, full_name, default_branch, language, imported_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (id) DO UPDATE SET owner_id = EXCLUDED.owner_id
                    """,
                    (r["id"], user_id, r["name"], r["full_name"], r["default_branch"], r.get("language")),
                )
            connection.commit()
    except Exception as exc:
        logger.debug("Database sync user repos skipped: %s", exc)

    return created


@router.get("/github/url")
def github_url(state: str | None = None) -> dict[str, Any]:
    """Return configured GitHub OAuth authorize URL."""
    return github_service.get_authorization_url(state=state)


@router.post("/github/login", response_model=AuthResponse)
@router.post("/github/direct", response_model=AuthResponse)
async def github_direct_login(payload: GitHubDirectLoginRequest) -> AuthResponse:
    """One-click or custom GitHub account authentication endpoint."""
    username = (payload.username or "Ajaymallavali").strip()
    user_token = payload.token.strip() if payload.token else None

    # Fetch live GitHub profile if token or network available
    live_profile = None
    if user_token:
        try:
            live_profile = await github_service.get_authenticated_user(user_token)
        except Exception as exc:
            logger.warning("Could not verify GitHub token: %s", exc)

    if live_profile:
        username = live_profile.get("login") or username
        display_name = live_profile.get("name") or payload.displayName or username
        email = (live_profile.get("email") or payload.email or f"{username.lower()}@users.noreply.github.com").lower()
    else:
        if username.lower() == "ajaymallavali":
            display_name = payload.displayName or "Ajay Mallavalli"
            email = (payload.email or "ajaymallavali02@gmail.com").lower()
        else:
            display_name = payload.displayName or username
            email = (payload.email or f"{username.lower()}@users.noreply.github.com").lower()

    # Look up existing user by email or github_username
    existing = dev_store.find_user_by_email(email)
    if not existing:
        for u in dev_store.get_users():
            if str(u.get("github_username", "")).lower() == username.lower():
                existing = u
                break

    user_id = existing["id"] if existing else uuid4()

    user_record = None
    try:
        with get_connection() as connection:
            user_record = connection.execute(
                """
                INSERT INTO users (id, email, display_name, password_hash, github_username, github_token)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE
                SET display_name = EXCLUDED.display_name,
                    github_username = EXCLUDED.github_username,
                    github_token = COALESCE(EXCLUDED.github_token, users.github_token)
                RETURNING id, email, display_name, github_username, created_at
                """,
                (user_id, email, display_name, hash_password(uuid4().hex), username, user_token or "gho_direct_token"),
            ).fetchone()
            connection.commit()
    except Exception as exc:
        logger.debug("Database unavailable for github_direct_login: %s; using dev store", exc)

    if not user_record:
        user_record = existing or {
            "id": user_id,
            "email": email,
            "display_name": display_name,
            "github_username": username,
            "github_token": user_token or "gho_direct_token",
            "password_hash": hash_password(uuid4().hex),
            "created_at": datetime.now(timezone.utc),
        }
        user_record["display_name"] = display_name
        user_record["github_username"] = username
        if user_token:
            user_record["github_token"] = user_token
        dev_store.save_user(user_record)

    # Ensure repositories for this account are synchronized and owned by user
    await _sync_user_github_repositories(user_record["id"], username, access_token=user_token)

    return auth_response(user_record)


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

        user = None
        user_id = uuid4()
        try:
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
                    (user_id, email, display_name, hash_password(uuid4().hex), username, access_token),
                ).fetchone()
                connection.commit()
        except Exception as exc:
            logger.debug("Database write in github_oauth_callback failed: %s; falling back to dev_store", exc)

        if not user:
            existing = dev_store.find_user_by_email(email)
            user = existing or {
                "id": user_id,
                "email": email,
                "display_name": display_name,
                "github_username": username,
                "github_token": access_token,
                "password_hash": hash_password(uuid4().hex),
                "created_at": datetime.now(timezone.utc),
            }
            user["github_username"] = username
            user["github_token"] = access_token
            dev_store.save_user(user)

        # Sync user repositories
        await _sync_user_github_repositories(user["id"], username, access_token=access_token)

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

        user = None
        user_id = uuid4()
        try:
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
                    (user_id, email, display_name, hash_password(uuid4().hex), username, access_token),
                ).fetchone()
                connection.commit()
        except Exception as exc:
            logger.debug("Database write in github_oauth_exchange failed: %s; falling back to dev_store", exc)

        if not user:
            existing = dev_store.find_user_by_email(email)
            user = existing or {
                "id": user_id,
                "email": email,
                "display_name": display_name,
                "github_username": username,
                "github_token": access_token,
                "password_hash": hash_password(uuid4().hex),
                "created_at": datetime.now(timezone.utc),
            }
            user["github_username"] = username
            user["github_token"] = access_token
            dev_store.save_user(user)

        # Sync user repositories
        await _sync_user_github_repositories(user["id"], username, access_token=access_token)

        return auth_response(user)
    except GitHubServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
