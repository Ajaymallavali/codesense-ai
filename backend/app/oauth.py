import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


class GoogleVerificationError(Exception):
    """Raised when Google ID token fails validation."""
    pass


async def verify_google_id_token(credential: str) -> dict[str, Any]:
    """
    Verify Google OAuth ID Token server-side via Google's tokeninfo API.
    Validates signature, expiration, issuer, and audience.
    """
    token = credential.strip()
    if not token:
        raise GoogleVerificationError("Google credential token cannot be empty.")

    # Check for local dev mock token
    if token == "mock-google-token":
        if settings.environment == "development":
            logger.info("Accepting mock-google-token in development environment mode.")
            return {
                "email": "demo.user@example.com",
                "displayName": "Google Demo User",
                "sub": "mock-google-sub-12345",
                "picture": None,
            }
        raise GoogleVerificationError("Mock tokens are not accepted in production.")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(GOOGLE_TOKENINFO_URL, params={"id_token": token})
            if not res.is_success:
                logger.warning(f"Google tokeninfo rejected token: HTTP {res.status_code}")
                raise GoogleVerificationError("Google ID token is invalid or expired.")

            data = res.json()

            # Verify email presence and verification status
            email = data.get("email")
            email_verified = data.get("email_verified")
            if not email or str(email_verified).lower() != "true":
                raise GoogleVerificationError("Google account email is not verified.")

            # Verify audience if client ID is configured
            if settings.google_client_id:
                aud = data.get("aud")
                if aud != settings.google_client_id:
                    logger.warning(f"Google token audience mismatch: expected {settings.google_client_id}, got {aud}")
                    raise GoogleVerificationError("Google token audience does not match configured client ID.")

            name = data.get("name") or data.get("given_name") or email.split("@")[0]
            return {
                "email": email.lower(),
                "displayName": name.strip(),
                "sub": data.get("sub"),
                "picture": data.get("picture"),
            }
    except GoogleVerificationError:
        raise
    except Exception as exc:
        logger.error(f"Failed to connect to Google OAuth verification endpoint: {exc}")
        raise GoogleVerificationError(f"Google OAuth verification failed: {str(exc)}") from exc
