"""Notion integration — sync meeting notes, summaries, and action items to Notion pages."""
import httpx
import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status

from routes.deps import require_authentication
from routes.integration_helpers import get_integration_config, save_integration_config, delete_integration_config
from security import log_audit_event
from security.auth import User

logger = logging.getLogger("routes.notion")

router = APIRouter()

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _notion_headers(api_key: str) -> dict:
    """Build standard Notion API headers."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


@router.get("/notion/status")
async def get_notion_status(user: User = Depends(require_authentication)):
    """Check Notion integration status."""
    cfg = await get_integration_config(user.id, "notion")
    if not cfg["connected"]:
        return {
            "status": "not_configured",
            "connected": False,
            "workspace_id": None,
        }
    config = cfg.get("config", {})
    return {
        "status": "connected",
        "connected": True,
        "workspace_id": config.get("workspace_id"),
    }


@router.post("/notion/connect")
async def connect_notion(
    body: dict = Body(...),
    user: User = Depends(require_authentication),
):
    """Connect a Notion workspace. Body: {api_key, workspace_id}."""
    api_key = body.get("api_key")
    workspace_id = body.get("workspace_id")

    if not api_key:
        raise HTTPException(status_code=400, detail="api_key is required")
    if not workspace_id:
        raise HTTPException(status_code=400, detail="workspace_id is required")

    # Validate the key by calling the /users/me endpoint
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{NOTION_API_BASE}/users/me",
                headers=_notion_headers(api_key),
                timeout=10.0,
            )
            if resp.status_code != 200:
                logger.warning("[Notion] Validation failed: %s", resp.status_code)
                raise HTTPException(status_code=400, detail="Invalid Notion API key")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[Notion] Connection check error: %s", str(exc))
        raise HTTPException(status_code=502, detail="Could not reach Notion API")

    await save_integration_config(
        user.id, "notion",
        config={"workspace_id": workspace_id},
        secrets={"api_key": api_key},
        enabled=True,
    )

    log_audit_event("notion_connect", user.username, "notion_connected", success=True)
    logger.info("[Notion] Workspace %s connected for user %s", workspace_id, user.username)  # lgtm[py/log-injection]

    return {"status": "connected", "workspace_id": workspace_id}


@router.post("/notion/sync")
async def sync_to_notion(
    body: dict = Body(...),
    user: User = Depends(require_authentication),
):
    """Sync meeting notes / summary to a Notion page.

    Body: {conversation_id, page_id, title, content}
    """
    cfg = await get_integration_config(user.id, "notion")
    if not cfg["connected"]:
        raise HTTPException(status_code=400, detail="Notion not configured. Use /notion/connect first.")

    api_key = cfg.get("secrets", {}).get("api_key")
    if not api_key:
        raise HTTPException(status_code=400, detail="Notion API key not found. Re-configure Notion.")

    conversation_id = body.get("conversation_id")
    page_id = body.get("page_id")
    title = body.get("title", "Meeting Notes")
    content = body.get("content", "")

    if not page_id:
        raise HTTPException(status_code=400, detail="page_id is required")

    notion_payload = {
        "parent": {"page_id": page_id},
        "properties": {
            "title": {
                "title": [
                    {
                        "text": {
                            "content": title,
                        },
                    },
                ],
            },
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": content[:2000]},
                        },
                    ],
                },
            },
        ],
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{NOTION_API_BASE}/pages",
                headers=_notion_headers(api_key),
                json=notion_payload,
                timeout=15.0,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                log_audit_event("notion_sync", user.username, "notion_page_created", success=True)
                logger.info("[Notion] Synced conversation %s to page %s", conversation_id, page_id)  # lgtm[py/log-injection]
                return {
                    "status": "synced",
                    "notion_page_id": data.get("id"),
                    "conversation_id": conversation_id,
                    "url": data.get("url"),
                }
            else:
                detail = resp.json().get("message", resp.text) if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                logger.error("[Notion] Sync failed (%s): %s", resp.status_code, detail)
                raise HTTPException(status_code=502, detail=f"Notion API error: {detail}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[Notion] Sync error: %s", str(exc))
        raise HTTPException(status_code=502, detail="Failed to sync to Notion")


@router.get("/notion/pages")
async def list_notion_pages(
    page_size: int = 50,
    user: User = Depends(require_authentication),
):
    """List Notion pages available for syncing."""
    cfg = await get_integration_config(user.id, "notion")
    if not cfg["connected"]:
        raise HTTPException(status_code=400, detail="Notion not configured. Use /notion/connect first.")

    api_key = cfg.get("secrets", {}).get("api_key")
    if not api_key:
        raise HTTPException(status_code=400, detail="Notion API key not found. Re-configure Notion.")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{NOTION_API_BASE}/search",
                headers=_notion_headers(api_key),
                json={
                    "filter": {
                        "property": "object",
                        "value": "page",
                    },
                    "page_size": min(page_size, 100),
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                pages = []
                for result in data.get("results", []):
                    page_title = ""
                    props = result.get("properties", {})
                    title_prop = props.get("title", {})
                    if title_prop.get("title"):
                        page_title = "".join(t.get("plain_text", "") for t in title_prop["title"])
                    pages.append({
                        "id": result.get("id"),
                        "title": page_title,
                        "url": result.get("url"),
                        "created_time": result.get("created_time"),
                        "last_edited_time": result.get("last_edited_time"),
                    })
                return {"pages": pages, "total": len(pages)}
            else:
                logger.error("[Notion] List pages failed: %s", resp.status_code)
                raise HTTPException(status_code=502, detail="Failed to list Notion pages")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[Notion] List pages error: %s", str(exc))
        raise HTTPException(status_code=502, detail="Failed to list Notion pages")


@router.delete("/notion/disconnect")
async def disconnect_notion(user: User = Depends(require_authentication)):
    """Disconnect Notion integration."""
    await delete_integration_config(user.id, "notion")
    log_audit_event("notion_disconnect", user.username, "notion_disconnected", success=True)
    logger.info("[Notion] Disconnected for user %s", user.username)
    return {"status": "disconnected"}