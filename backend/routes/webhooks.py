"""Webhook endpoints for Zapier and automation integrations."""
import logging
import time
import uuid
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from routes.deps import require_authentication
from security.auth import User
from pydantic import BaseModel, Field

logger = logging.getLogger("routes.webhooks")

router = APIRouter()


class WebhookSigningRequest(BaseModel):
    secret: str = Field(default="", max_length=1024)

# Webhook subscription store (production: database)
_webhook_subscriptions: Dict[str, dict] = {}


@router.post("/webhooks/subscribe")
async def subscribe_webhook(
    request: Request,
    user: User = Depends(require_authentication),
    url: str = Query(..., description="Webhook callback URL"),
    events: str = Query("transcript.ready,summary.ready", description="Comma-separated event types"),
    signing: WebhookSigningRequest | None = None,
):
    """Subscribe to webhook events (Zapier-compatible)."""
    if "secret" in request.query_params:
        raise HTTPException(422, "Send signing secrets in the JSON body")
    secret = signing.secret if signing else ""
    webhook_id = str(uuid.uuid4())

    _webhook_subscriptions[webhook_id] = {
        "id": webhook_id,
        "owner_id": str(user.id),
        "url": url,
        "events": [e.strip() for e in events.split(",")],
        "secret": secret or str(uuid.uuid4()),
        "created_at": time.time(),
        "active": True,
    }

    return {
        "id": webhook_id,
        "url": url,
        "events": _webhook_subscriptions[webhook_id]["events"],
        "secret": _webhook_subscriptions[webhook_id]["secret"],
    }


@router.get("/webhooks")
async def list_webhooks(user: User = Depends(require_authentication)):
    """List the authenticated user's webhook subscriptions."""
    return {
        "webhooks": [
            {
                "id": w["id"],
                "url": w["url"],
                "events": w["events"],
                "active": w["active"],
            }
            for w in _webhook_subscriptions.values()
            if w.get("owner_id") == str(user.id)
        ]
    }


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, user: User = Depends(require_authentication)):
    """Delete a webhook subscription."""
    webhook = _webhook_subscriptions.get(webhook_id)
    if webhook and webhook.get("owner_id") == str(user.id):
        del _webhook_subscriptions[webhook_id]
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Webhook not found")


@router.get("/webhooks/events")
async def list_webhook_events():
    """List available webhook event types (Zapier triggers)."""
    return {
        "events": [
            {"type": "transcript.ready", "description": "Fired when a transcript is completed"},
            {"type": "summary.ready", "description": "Fired when AI summary is generated"},
            {"type": "action_items.extracted", "description": "Fired when action items are extracted"},
            {"type": "interview.completed", "description": "Fired when an interview session ends"},
            {"type": "conversation.saved", "description": "Fired when a conversation is saved"},
        ]
    }


@router.post("/webhooks/test")
async def test_webhook(
    event_type: str = Query("transcript.ready"),
    user: User = Depends(require_authentication),
):
    """Preview a sample event and matching owned webhook subscriptions."""
    sample_payloads = {
        "transcript.ready": {
            "event": "transcript.ready",
            "data": {
                "id": "test-123",
                "title": "Sample Meeting Transcript",
                "duration_seconds": 300,
                "language": "en",
                "word_count": 500,
            }
        },
        "summary.ready": {
            "event": "summary.ready",
            "data": {
                "id": "test-123",
                "title": "Sample Meeting Summary",
                "action_items_count": 3,
                "key_decisions_count": 2,
            }
        },
        "action_items.extracted": {
            "event": "action_items.extracted",
            "data": {
                "conversation_id": "test-123",
                "items": [
                    {"text": "Follow up on proposal", "priority": "high"},
                    {"text": "Schedule review meeting", "priority": "medium"},
                ]
            }
        },
    }

    payload = sample_payloads.get(event_type, {"event": event_type, "data": {}})

    # Preview matching subscriptions; delivery is handled separately.
    matching = 0
    for webhook in _webhook_subscriptions.values():
        if webhook.get("owner_id") != str(user.id) or not webhook["active"]:
            continue
        if event_type in webhook["events"] or "*" in webhook["events"]:
            matching += 1

    return {"status": "preview", "event": event_type, "matching_webhooks": matching,
            "webhooks_notified": 0, "payload": payload}