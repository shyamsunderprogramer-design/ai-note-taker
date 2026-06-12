"""
Route module for the MCP (Model Context Protocol) server endpoints.
Exposes the project's transcripts + insights to external LLM clients
over the MCP standard. This is the HTTP wrapper; the real protocol
sits on top of `modules.platform.mcp_server`.

Endpoints:
  GET  /mcp/status
  GET  /mcp/tools
  GET  /mcp/resources
  POST /mcp/tools/{tool_name}
"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from security import ErrorCode, error_response
from security.auth import User
from security import get_current_user

# Local require_authentication (mirrors routes/auth.py pattern)
import os
from fastapi import status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends as _Depends

_security_bearer = HTTPBearer(auto_error=False)


async def get_token_from_request(credentials: HTTPAuthorizationCredentials = _Depends(_security_bearer)) -> str:
    if credentials:
        return credentials.credentials
    return None


async def require_authentication(token: str = _Depends(get_token_from_request)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

logger = logging.getLogger("routes.mcp")

router = APIRouter()

# MCP server module — optional dependency
try:
    from modules.platform.mcp_server import (
        MCPServer, MCPTool, MCPResource,
        create_mcp_server, mcp_server,
        search_transcripts_handler, get_summary_handler,
        list_action_items_handler, get_interview_notes_handler,
        ask_about_conversation_handler,
    )
    # `get_status` may or may not exist in the module — the original
    # main.py call site had the same fragility, so we wrap the import.
    try:
        from modules.platform.mcp_server import get_status as _mcp_get_status
    except ImportError:
        def _mcp_get_status():
            return {"available": True, "note": "get_status() not exposed by mcp_server module"}
    MCP_AVAILABLE = True
except ImportError as e:
    MCP_AVAILABLE = False
    logger.warning("[MCP] Module not available: %s", str(e))

    def _mcp_get_status():
        return {"available": False, "error": "MCP module not installed"}


@router.get("/mcp/status")
async def mcp_status():
    """Get MCP server status."""
    if not MCP_AVAILABLE:
        return {"available": False, "error": "MCP module not installed"}
    return _mcp_get_status()


@router.post("/mcp/tools/{tool_name}")
async def mcp_tool_call(tool_name: str, body: dict, user: User = Depends(require_authentication)):
    """Call an MCP tool via HTTP."""
    if not MCP_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "MCP not available", status_code=503)

    try:
        from modules.platform.mcp_server import mcp_server as _mcp
        if tool_name not in _mcp.tools:
            return error_response(ErrorCode.NOT_FOUND, f"Tool not found: {tool_name}", status_code=404)

        result = await _mcp.tools[tool_name].handler(body)
        return {"tool": tool_name, "result": result}
    except Exception as e:
        logger.error("[MCP] Tool call error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "Tool execution failed", status_code=500)


@router.get("/mcp/tools")
async def mcp_tools_list(user: User = Depends(require_authentication)):
    """List all available MCP tools."""
    if not MCP_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "MCP not available", status_code=503)

    try:
        from modules.platform.mcp_server import mcp_server as _mcp
        tools = []
        for tool in _mcp.tools.values():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            })
        return {"tools": tools}
    except Exception as e:
        logger.error("[MCP] Tools list error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "Failed to list tools", status_code=500)


@router.get("/mcp/resources")
async def mcp_resources_list(user: User = Depends(require_authentication)):
    """List all available MCP resources."""
    if not MCP_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "MCP not available", status_code=503)

    try:
        from modules.platform.mcp_server import mcp_server as _mcp
        resources = []
        for resource in _mcp.resources.values():
            resources.append({
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mime_type": resource.mime_type,
            })
        return {"resources": resources}
    except Exception as e:
        logger.error("[MCP] Resources list error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "Failed to list resources", status_code=500)
