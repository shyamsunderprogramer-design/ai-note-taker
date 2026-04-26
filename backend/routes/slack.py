"""Slack integration — post transcripts, summaries, and action items to channels."""
import httpx
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from routes.deps import require_authentication
from routes.integration_helpers import get_integration_config, save_integration_config, delete_integration_config
from security import log_audit_event
from security.auth import User

logger = logging.getLogger("routes.slack")

router = APIRouter()


@router.get("/slack/status")
async def get_slack_status(user: User = Depends(require_authentication)):
    """Check Slack integration status."""
    cfg = await get_integration_config(user.id, "slack")
    if not cfg["connected"]:
        return {
            "connected": False,
            "webhook_url": False,
            "default_channel": None,
            "auto_post": False,
        }
    secrets = cfg.get("secrets", {})
    config = cfg.get("config", {})
    return {
        "connected": True,
        "webhook_url": bool(secrets.get("webhook_url")),
        "default_channel": config.get("default_channel"),
        "auto_post": config.get("auto_post", False),
    }


@router.post("/slack/configure")
async def configure_slack(
    webhook_url: str = Query(..., description="Slack incoming webhook URL"),
    default_channel: str = Query("", description="Default channel name"),
    auto_post: bool = Query(False, description="Auto-post after meetings"),
    user: User = Depends(require_authentication),
):
    """Configure Slack integration with webhook URL."""
    if not webhook_url.startswith("https://hooks.slack.com/"):
        raise HTTPException(status_code=400, detail="Invalid Slack webhook URL format")

    await save_integration_config(
        user.id, "slack",
        config={"default_channel": default_channel, "auto_post": auto_post},
        secrets={"webhook_url": webhook_url},
        enabled=True,
    )

    log_audit_event("slack_configure", user.username, "slack_configured", success=True)

    return {"status": "configured", "auto_post": auto_post}


@router.post("/slack/post")
async def post_to_slack(
    body: dict,
    user: User = Depends(require_authentication),
):
    """Post a message to Slack."""
    cfg = await get_integration_config(user.id, "slack")
    if not cfg["connected"]:
        raise HTTPException(status_code=400, detail="Slack not configured. Use /slack/configure first.")

    webhook_url = cfg.get("secrets", {}).get("webhook_url")
    if not webhook_url:
        raise HTTPException(status_code=400, detail="Slack webhook URL not found. Re-configure Slack.")

    message_type = body.get("type", "summary")
    title = body.get("title", "Meeting Update")
    content = body.get("content", "")

    slack_message = _format_slack_message(message_type, title, content, user.username)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(  # nosec B611 — Slack webhook URL validated above
                webhook_url,
                json={"text": slack_message},
                timeout=10.0,
            )
            if response.status_code == 200:
                log_audit_event("slack_post", user.username, "slack_message_sent", success=True)
                return {"status": "sent", "message_type": message_type}
            else:
                return {"status": "error", "detail": f"Slack returned {response.status_code}"}
    except Exception as e:
        logger.error("[Slack] Post failed: %s", str(e))
        return {"status": "error", "detail": "Failed to send to Slack"}


@router.delete("/slack/disconnect")
async def disconnect_slack(user: User = Depends(require_authentication)):
    """Disconnect Slack integration."""
    await delete_integration_config(user.id, "slack")
    log_audit_event("slack_disconnect", user.username, "slack_disconnected", success=True)
    return {"status": "disconnected"}


def _format_slack_message(msg_type: str, title: str, content: str, username: str) -> str:
    """Format a message for Slack."""
    if msg_type == "summary":
        return f"*{title}*\nPosted by {username}\n\n{content[:3000]}"
    elif msg_type == "action_items":
        return f"*Action Items — {title}*\nPosted by {username}\n\n{content[:3000]}"
    elif msg_type == "transcript":
        preview = content[:500] + "..." if len(content) > 500 else content
        return f"*Transcript — {title}*\nPosted by {username}\n\n```\n{preview}\n```"
    return f"*{title}*\n{content[:3000]}"