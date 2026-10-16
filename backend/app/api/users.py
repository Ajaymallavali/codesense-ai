from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.common import user_response
from app.database import get_connection
from app.schemas import UpdatePasswordRequest, UpdateProfileRequest, UserResponse
from app.security import get_current_user, hash_password, verify_password

router = APIRouter(tags=["users"])


@router.put("/profile", response_model=UserResponse)
def update_profile(
    payload: UpdateProfileRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UserResponse:
    try:
        with get_connection() as connection:
            user = connection.execute(
                """
                UPDATE users
                SET display_name = %s, github_token = %s, github_username = %s
                WHERE id = %s
                RETURNING id, email, display_name, github_username, created_at
                """,
                (payload.displayName.strip(), payload.githubToken, payload.githubUsername, current_user["id"]),
            ).fetchone()
            connection.commit()
            if user:
                return user_response(user)
    except Exception:
        pass

    updated = {
        "id": current_user["id"],
        "email": current_user["email"],
        "display_name": payload.displayName.strip(),
        "github_username": payload.githubUsername or "Ajaymallavali",
        "created_at": current_user.get("created_at"),
    }
    return user_response(updated)


@router.put("/password")
def update_password(
    payload: UpdatePasswordRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    if not verify_password(payload.currentPassword, current_user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")

    with get_connection() as connection:
        connection.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hash_password(payload.newPassword), current_user["id"]),
        )
        connection.commit()
    return {"message": "Password updated"}
