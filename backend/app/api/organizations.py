import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.database import get_connection
from app.dev_store import dev_store
from app.security import get_current_user

router = APIRouter(tags=["organizations"])
logger = logging.getLogger(__name__)


class CreateOrgRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str | None = None


class AddMemberRequest(BaseModel):
    email: str = Field(min_length=3)
    role: str = Field(default="MEMBER", pattern="^(ADMIN|REVIEWER|MEMBER)$")


class OrgResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    role: str
    createdAt: str


@router.post("", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: CreateOrgRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> OrgResponse:
    org_id = uuid4()
    member_id = uuid4()
    slug = (payload.slug or payload.name.lower().replace(" ", "-")).strip()
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO organizations (id, name, slug)
                VALUES (%s, %s, %s)
                """,
                (org_id, payload.name.strip(), slug),
            )
            connection.execute(
                """
                INSERT INTO organization_members (id, organization_id, user_id, role)
                VALUES (%s, %s, %s, 'ADMIN')
                """,
                (member_id, org_id, current_user["id"]),
            )
            connection.commit()
            return OrgResponse(
                id=org_id,
                name=payload.name.strip(),
                slug=slug,
                role="ADMIN",
                createdAt=now_iso,
            )
    except Exception as exc:
        logger.debug(f"Database unavailable for create_organization: {exc}; saving to dev_store")

    org_record = {
        "id": str(org_id),
        "name": payload.name.strip(),
        "slug": slug,
        "created_at": now_iso,
    }
    dev_store.save_organization(org_record)
    dev_store.add_organization_member({
        "id": str(member_id),
        "organization_id": str(org_id),
        "user_id": str(current_user["id"]),
        "role": "ADMIN",
        "created_at": now_iso,
    })

    return OrgResponse(
        id=org_id,
        name=payload.name.strip(),
        slug=slug,
        role="ADMIN",
        createdAt=now_iso,
    )


@router.get("", response_model=list[OrgResponse])
def list_organizations(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[OrgResponse]:
    user_id = str(current_user["id"])
    try:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT o.id, o.name, o.slug, o.created_at, m.role
                FROM organizations o
                JOIN organization_members m ON m.organization_id = o.id
                WHERE m.user_id = %s
                ORDER BY o.created_at DESC
                """,
                (user_id,),
            ).fetchall()
            if rows:
                return [
                    OrgResponse(
                        id=r["id"],
                        name=r["name"],
                        slug=r["slug"],
                        role=r["role"],
                        createdAt=r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
                    )
                    for r in rows
                ]
    except Exception as exc:
        logger.debug(f"Database unavailable for list_organizations: {exc}; reading dev_store")

    # Read from dev_store
    org_members = [m for m in dev_store.get_organization_members() if str(m.get("user_id")) == user_id]
    result: list[OrgResponse] = []
    orgs = {str(o.get("id")): o for o in dev_store.get_organizations()}

    for m in org_members:
        org_id_str = str(m.get("organization_id"))
        if org_id_str in orgs:
            o = orgs[org_id_str]
            result.append(
                OrgResponse(
                    id=UUID(org_id_str),
                    name=o.get("name", "Team"),
                    slug=o.get("slug", "team"),
                    role=m.get("role", "MEMBER"),
                    createdAt=o.get("created_at", datetime.now(timezone.utc).isoformat()),
                )
            )

    if not result:
        # Default starter organization for development
        default_org_id = uuid4()
        now_iso = datetime.now(timezone.utc).isoformat()
        default_org = {
            "id": str(default_org_id),
            "name": "Ajay's Engineering Team",
            "slug": "ajay-team",
            "created_at": now_iso,
        }
        dev_store.save_organization(default_org)
        dev_store.add_organization_member({
            "id": str(uuid4()),
            "organization_id": str(default_org_id),
            "user_id": user_id,
            "role": "ADMIN",
            "created_at": now_iso,
        })
        result.append(
            OrgResponse(
                id=default_org_id,
                name="Ajay's Engineering Team",
                slug="ajay-team",
                role="ADMIN",
                createdAt=now_iso,
            )
        )

    return result


@router.post("/{org_id}/members")
def add_member(
    org_id: UUID,
    payload: AddMemberRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    member_user = dev_store.find_user_by_email(payload.email.strip().lower())
    target_user_id = member_user.get("id") if member_user else uuid4()

    now_iso = datetime.now(timezone.utc).isoformat()
    dev_store.add_organization_member({
        "id": str(uuid4()),
        "organization_id": str(org_id),
        "user_id": str(target_user_id),
        "role": payload.role,
        "email": payload.email.strip().lower(),
        "created_at": now_iso,
    })

    return {
        "status": "success",
        "message": f"Added {payload.email} as {payload.role} to organization.",
        "organizationId": str(org_id),
        "role": payload.role,
    }
