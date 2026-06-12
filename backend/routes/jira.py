"""Jira integration — create issues from action items and sync meeting outcomes to Jira."""
import base64
import httpx
import logging
import re
from typing import Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException

from routes.deps import require_authentication
from routes.integration_helpers import get_integration_config, save_integration_config, delete_integration_config
from security import log_audit_event
from security.auth import User

logger = logging.getLogger("routes.jira")

router = APIRouter()

# In-memory conversation store for extracting action items (production: database)
_conversations: Dict[str, dict] = {}


def _jira_headers(email: str, api_token: str) -> dict:
    """Build Jira API headers with Basic auth."""
    credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    return {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _jira_api_url(base_url: str, path: str) -> str:
    """Build a full Jira API URL from base URL and path."""
    base = base_url.rstrip("/")
    return f"{base}/rest/api/3{path}"


# ---------- status ----------

@router.get("/jira/status")
async def get_jira_status(user: User = Depends(require_authentication)):
    """Check Jira integration status."""
    cfg = await get_integration_config(user.id, "jira")
    if not cfg["connected"]:
        return {
            "status": "not_configured",
            "connected": False,
            "base_url": None,
        }
    config = cfg.get("config", {})
    return {
        "status": "connected",
        "connected": True,
        "base_url": config.get("base_url"),
        "email": config.get("email"),
    }


# ---------- connect ----------

@router.post("/jira/connect")
async def connect_jira(
    body: dict = Body(...),
    user: User = Depends(require_authentication),
):
    """Connect a Jira workspace. Body: {base_url, email, api_token}."""
    base_url = body.get("base_url")
    email = body.get("email")
    api_token = body.get("api_token")

    if not base_url:
        raise HTTPException(status_code=400, detail="base_url is required")
    if not email:
        raise HTTPException(status_code=400, detail="email is required")
    if not api_token:
        raise HTTPException(status_code=400, detail="api_token is required")

    # Validate credentials by fetching server info
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(  # nosec B611; lgtm[py/request-forgery] — user-configured Jira instance
                _jira_api_url(base_url, "/serverInfo"),
                headers=_jira_headers(email, api_token),
                timeout=10.0,
            )
            if resp.status_code != 200:
                logger.warning("[Jira] Validation failed: %s", resp.status_code)
                raise HTTPException(status_code=400, detail="Invalid Jira credentials or base URL")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[Jira] Connection check error: %s", str(exc))
        raise HTTPException(status_code=502, detail="Could not reach Jira API")

    await save_integration_config(
        user.id, "jira",
        config={"base_url": base_url, "email": email},
        secrets={"api_token": api_token},
        enabled=True,
    )

    log_audit_event("jira_connect", user.username, "jira_connected", success=True)
    logger.info("[Jira] Workspace %s connected for user %s", base_url, user.username)  # lgtm[py/log-injection]

    return {"status": "connected", "base_url": base_url}


# ---------- create issue ----------

@router.post("/jira/create-issue")
async def create_jira_issue(
    body: dict = Body(...),
    user: User = Depends(require_authentication),
):
    """Create a Jira issue from action items.

    Body: {project_key, summary, description, issue_type, priority}
    """
    cfg = await get_integration_config(user.id, "jira")
    if not cfg["connected"]:
        raise HTTPException(status_code=400, detail="Jira not configured. Use /jira/connect first.")

    config = cfg.get("config", {})
    secrets = cfg.get("secrets", {})
    api_token = secrets.get("api_token")
    if not api_token:
        raise HTTPException(status_code=400, detail="Jira API token not found. Re-configure Jira.")

    base_url = config.get("base_url")
    email = config.get("email")

    project_key = body.get("project_key")
    summary = body.get("summary")
    description = body.get("description", "")
    issue_type = body.get("issue_type", "Task")
    priority = body.get("priority", "Medium")

    if not project_key:
        raise HTTPException(status_code=400, detail="project_key is required")
    if not summary:
        raise HTTPException(status_code=400, detail="summary is required")

    priority_map = {
        "Highest": "1", "High": "2", "Medium": "3", "Low": "4", "Lowest": "5",
    }
    priority_id = priority_map.get(priority, "3")

    jira_payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": description or summary,
                            },
                        ],
                    },
                ],
            },
            "issuetype": {"name": issue_type},
            "priority": {"id": priority_id},
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(  # nosec B611 — user-configured Jira instance
                _jira_api_url(base_url, "/issue"),
                headers=_jira_headers(email, api_token),
                json=jira_payload,
                timeout=15.0,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                log_audit_event("jira_create_issue", user.username, "jira_issue_created", success=True)
                logger.info("[Jira] Created issue %s in %s", data.get("key"), project_key)  # lgtm[py/log-injection]
                return {
                    "status": "created",
                    "issue_key": data.get("key"),
                    "issue_id": data.get("id"),
                    "self": data.get("self"),
                }
            else:
                detail = resp.json().get("errorMessages", [resp.text]) if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                if isinstance(detail, list):
                    detail = "; ".join(detail)
                logger.error("[Jira] Create issue failed (%s): %s", resp.status_code, detail)
                raise HTTPException(status_code=502, detail=f"Jira API error: {detail}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[Jira] Create issue error: %s", str(exc))
        raise HTTPException(status_code=502, detail="Failed to create Jira issue")


# ---------- list projects ----------

@router.get("/jira/projects")
async def list_jira_projects(user: User = Depends(require_authentication)):
    """List Jira projects accessible to the connected user."""
    cfg = await get_integration_config(user.id, "jira")
    if not cfg["connected"]:
        raise HTTPException(status_code=400, detail="Jira not configured. Use /jira/connect first.")

    config = cfg.get("config", {})
    secrets = cfg.get("secrets", {})
    api_token = secrets.get("api_token")
    if not api_token:
        raise HTTPException(status_code=400, detail="Jira API token not found. Re-configure Jira.")

    base_url = config.get("base_url")
    email = config.get("email")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(  # nosec B611 — user-configured Jira instance
                _jira_api_url(base_url, "/project"),
                headers=_jira_headers(email, api_token),
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                projects = [
                    {
                        "key": p.get("key"),
                        "name": p.get("name"),
                        "project_type": p.get("projectTypeKey"),
                        "style": p.get("style"),
                    }
                    for p in data
                ]
                return {"projects": projects, "total": len(projects)}
            else:
                logger.error("[Jira] List projects failed: %s", resp.status_code)
                raise HTTPException(status_code=502, detail="Failed to list Jira projects")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[Jira] List projects error: %s", str(exc))
        raise HTTPException(status_code=502, detail="Failed to list Jira projects")


# ---------- sync action items ----------

@router.post("/jira/sync-action-items")
async def sync_action_items(
    body: dict = Body(...),
    user: User = Depends(require_authentication),
):
    """Sync extracted action items from a conversation to Jira as sub-tasks.

    Body: {conversation_id, project_key}
    """
    cfg = await get_integration_config(user.id, "jira")
    if not cfg["connected"]:
        raise HTTPException(status_code=400, detail="Jira not configured. Use /jira/connect first.")

    config = cfg.get("config", {})
    secrets = cfg.get("secrets", {})
    api_token = secrets.get("api_token")
    base_url = config.get("base_url")
    email = config.get("email")

    conversation_id = body.get("conversation_id")
    project_key = body.get("project_key")

    if not conversation_id:
        raise HTTPException(status_code=400, detail="conversation_id is required")
    if not project_key:
        raise HTTPException(status_code=400, detail="project_key is required")

    # Retrieve conversation and extract action items
    conversation = _conversations.get(conversation_id)
    if not conversation:
        logger.warning("[Jira] Conversation %s not found in local store", conversation_id)  # lgtm[py/log-injection]
        return {
            "status": "no_conversation",
            "detail": f"Conversation {conversation_id} not found. Action items could not be extracted.",
            "created_issues": [],
        }

    action_items = _extract_action_items(conversation)
    if not action_items:
        return {
            "status": "no_action_items",
            "detail": "No action items found in the conversation.",
            "created_issues": [],
        }

    created_issues: List[dict] = []

    try:
        async with httpx.AsyncClient() as client:
            for item in action_items:
                jira_payload = {
                    "fields": {
                        "project": {"key": project_key},
                        "summary": item[:255],
                        "description": {
                            "type": "doc",
                            "version": 1,
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": item,
                                        },
                                    ],
                                },
                            ],
                        },
                        "issuetype": {"name": "Sub-task"},
                    },
                }

                resp = await client.post(  # nosec B611 — user-configured Jira instance
                    _jira_api_url(base_url, "/issue"),
                    headers=_jira_headers(email, api_token),
                    json=jira_payload,
                    timeout=15.0,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    created_issues.append({
                        "issue_key": data.get("key"),
                        "issue_id": data.get("id"),
                        "summary": item[:255],
                    })
                else:
                    logger.error("[Jira] Sub-task creation failed (%s) for: %s", resp.status_code, item[:80])

    except Exception as exc:
        logger.error("[Jira] Sync action items error: %s", str(exc))
        raise HTTPException(status_code=502, detail="Failed to sync action items to Jira")

    log_audit_event("jira_sync_action_items", user.username, "jira_action_items_synced", success=True)
    logger.info(  # lgtm[py/log-injection]
        "[Jira] Synced %d action items from conversation %s to %s",
        len(created_issues), conversation_id, project_key,
    )

    return {
        "status": "synced",
        "conversation_id": conversation_id,
        "project_key": project_key,
        "total_action_items": len(action_items),
        "created_issues": created_issues,
        "created_count": len(created_issues),
    }


# ---------- disconnect ----------

@router.delete("/jira/disconnect")
async def disconnect_jira(user: User = Depends(require_authentication)):
    """Disconnect Jira integration."""
    await delete_integration_config(user.id, "jira")
    log_audit_event("jira_disconnect", user.username, "jira_disconnected", success=True)
    logger.info("[Jira] Disconnected for user %s", user.username)
    return {"status": "disconnected"}


# ---------- helpers ----------

def _extract_action_items(conversation: dict) -> List[str]:
    """Extract action items from a stored conversation dict."""
    items: List[str] = []

    if conversation.get("action_items"):
        for ai in conversation["action_items"]:
            text = ai if isinstance(ai, str) else ai.get("text", "")
            if text.strip():
                items.append(text.strip())

    text_sources = [
        conversation.get("summary", ""),
        conversation.get("transcript", ""),
    ]
    combined = "\n".join(text_sources)

    if combined:
        patterns = [
            r"(?:^|\n)\s*- \[ \]\s*(.+)",
            r"(?:^|\n)\s*TODO:\s*(.+)",
            r"(?:^|\n)\s*Action(?:\s+item)?:\s*(.+)",
            r"(?:^|\n)\s*\d+\.\s*(.+)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, combined, re.IGNORECASE):
                candidate = match.group(1).strip()
                if candidate and candidate not in items:
                    items.append(candidate)

    return items