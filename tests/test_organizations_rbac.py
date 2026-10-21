import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_and_list_organizations(auth_headers):
    # 1. Create Organization
    res = client.post(
        "/api/organizations",
        headers=auth_headers,
        json={"name": "Antigravity Research Labs", "slug": "antigravity-labs"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Antigravity Research Labs"
    assert data["role"] == "ADMIN"
    org_id = data["id"]

    # 2. List Organizations
    list_res = client.get("/api/organizations", headers=auth_headers)
    assert list_res.status_code == 200
    orgs = list_res.json()
    assert any(o["id"] == org_id for o in orgs)

    # 3. Add Member with Role
    member_res = client.post(
        f"/api/organizations/{org_id}/members",
        headers=auth_headers,
        json={"email": "reviewer@example.com", "role": "REVIEWER"},
    )
    assert member_res.status_code == 200
    assert member_res.json()["status"] == "success"
    assert member_res.json()["role"] == "REVIEWER"
