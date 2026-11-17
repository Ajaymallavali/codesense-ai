import json
import uuid
from datetime import datetime, timezone
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.database import initialize_database
from app.dev_store import dev_store
from app.security import create_token


def test_alembic_migrations_tree():
    """Verify Alembic migration revisions link correctly from base to head."""
    alembic_cfg = Config("backend/alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)

    revisions = list(script.walk_revisions())
    rev_ids = [r.revision for r in revisions]

    assert "002_conversations_and_reports" in rev_ids
    assert "001_initial_schema" in rev_ids

    # 002 must have down_revision pointing to 001
    head_rev = script.get_revision("002_conversations_and_reports")
    assert head_rev.down_revision == "001_initial_schema"


def test_dev_store_persistence_across_reloads():
    """Verify that conversation messages and ownership persist across reload simulation."""
    conv_id = f"test-persist-{uuid.uuid4().hex[:8]}"
    user_id = str(uuid.uuid4())

    # Turn 1
    dev_store.save_conversation_message(
        conv_id,
        {"role": "user", "content": "How is billing calculated?"},
        user_id=user_id,
    )
    dev_store.save_conversation_message(
        conv_id,
        {
            "role": "assistant",
            "content": "Using calculate_sales_tax in src/billing.py",
            "citations": [{"filePath": "src/billing.py", "startLine": 1, "endLine": 15}],
        },
        user_id=user_id,
    )

    # Verification: Owner is user_id
    assert dev_store.get_conversation_owner(conv_id) == user_id
    msgs = dev_store.get_conversation_messages(conv_id)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["citations"][0]["filePath"] == "src/billing.py"

    # Turn 2
    dev_store.save_conversation_message(
        conv_id,
        {"role": "user", "content": "What is the tax rate?"},
        user_id=user_id,
    )
    updated_msgs = dev_store.get_conversation_messages(conv_id)
    assert len(updated_msgs) == 3


@pytest.mark.asyncio
async def test_conversation_api_authorization_and_persistence(backend_client):
    """Verify end-to-end API conversation message creation, history retrieval, and access control."""
    user_alpha = {
        "id": uuid.uuid4(),
        "email": "alpha_persist@codesense.dev",
        "display_name": "Alpha Persist",
        "github_username": "alpha_p",
        "github_token": "token-p1",
        "created_at": "2026-10-15T12:00:00Z",
    }
    user_beta = {
        "id": uuid.uuid4(),
        "email": "beta_persist@codesense.dev",
        "display_name": "Beta Persist",
        "github_username": "beta_p",
        "github_token": "token-p2",
        "created_at": "2026-10-15T12:00:00Z",
    }
    token_alpha = create_token(user_alpha)
    token_beta = create_token(user_beta)

    # User Alpha initiates chat
    chat_payload = {
        "query": "Explain database index performance",
        "conversationId": str(uuid.uuid4()),
    }
    res_chat = await backend_client.post(
        "/api/ai/chat",
        json=chat_payload,
        headers={"Authorization": f"Bearer {token_alpha}"},
    )
    assert res_chat.status_code == 200
    chat_data = res_chat.json()
    conv_id = chat_data["conversationId"]

    # User Alpha retrieves history -> 200 with 2 messages (user + assistant)
    res_hist = await backend_client.get(
        f"/api/ai/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token_alpha}"},
    )
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert len(hist_data["messages"]) >= 2
    assert hist_data["messages"][0]["role"] == "user"
    assert hist_data["messages"][1]["role"] == "assistant"

    # User Beta tries to access Alpha's conversation -> 403 Forbidden!
    res_forbidden = await backend_client.get(
        f"/api/ai/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token_beta}"},
    )
    assert res_forbidden.status_code == 403
    err_body = res_forbidden.json()
    assert "Access denied" in (err_body.get("message") or err_body.get("detail") or "")
