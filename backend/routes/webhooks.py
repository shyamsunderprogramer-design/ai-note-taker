"""Webhook endpoints for Zapier and automation integrations."""
import hmac
import hashlib
import json
import logging
import time
import uuid
from typing import Dict, List

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from security import get_current_user, log_audit_event
from security.auth import User

logger = logging.getLogger("routes.webhooks")

router = APIRouter()

# Webhook subscription store (production: database)
_webhook_subscriptions: Dict[str, dict] = {}
_event_log: List[Dict] = []


@router.post("/webhooks/subscribe")
async def subscribe_webhook(
    request: Request,
    url: str = Query(..., description="Webhook callback URL"),
    events: str = Query("transcript.ready,summary.ready", description="Comma-separated event types"),
    secret: str = Query("", description="HMAC signing secret"),
):
    """Subscribe to webhook events (Zapier-compatible)."""
    webhook_id = str(uuid.uuid4())[:8]

    _webhook_subscriptions[webhook_id] = {
        "id": webhook_id,
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
async def list_webhooks():
    """List all webhook subscriptions."""
    return {
        "webhooks": [
            {
                "id": w["id"],
                "url": w["url"],
                "events": w["events"],
                "active": w["active"],
            }
            for w in _webhook_subscriptions.values()
        ]
    }


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete a webhook subscription."""
    if webhook_id in _webhook_subscriptions:
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
):
    """Test a webhook by firing a sample event."""
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

    # Fire to all matching webhooks
    fired = 0
    for webhook in _webhook_subscriptions.values():
        if not webhook["active"]:
            continue
        if event_type in webhook["events"] or "*" in webhook["events"]:
            # In production: make async HTTP POST to webhook URL with HMAC signature
            fired += 1

    return {"status": "test_fired", "event": event_type, "webhooks_notified": fired, "payload": payload}