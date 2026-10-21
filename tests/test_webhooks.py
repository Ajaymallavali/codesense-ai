import hashlib
import hmac
import json
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_github_ping_webhook():
    response = client.post(
        "/api/webhooks/github",
        headers={"X-GitHub-Event": "ping"},
        json={"zen": "Non-blocking is better than blocking."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "Pong" in response.json()["message"]


def test_github_webhook_hmac_signature_validation():
    secret = "test-webhook-secret"
    settings.github_webhook_secret = secret

    payload = {
        "action": "opened",
        "number": 42,
        "pull_request": {
            "title": "Fix security vulnerability",
            "body": "Replaced eval with JSON.parse",
            "head": {"ref": "fix/security", "sha": "abc1234"},
        },
        "repository": {
            "full_name": "Ajaymallavali/codesense-ai",
            "name": "codesense-ai",
        },
    }
    body_bytes = json.dumps(payload).encode("utf-8")

    # 1. Invalid signature should return 401
    bad_res = client.post(
        "/api/webhooks/github",
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=invalidhexsignature",
        },
        content=body_bytes,
    )
    assert bad_res.status_code == 401

    # 2. Valid HMAC signature should return 200 and queue analysis
    valid_sig = "sha256=" + hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    good_res = client.post(
        "/api/webhooks/github",
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": valid_sig,
        },
        content=body_bytes,
    )
    assert good_res.status_code == 200
    assert good_res.json()["status"] == "queued"
    assert good_res.json()["pull_number"] == 42
    assert good_res.json()["repository"] == "Ajaymallavali/codesense-ai"

    # Reset secret
    settings.github_webhook_secret = ""
