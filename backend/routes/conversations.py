"""Route module for conversation export/import and document management."""
import json
import logging
import os
import shutil
import time

from fastapi import APIRouter, Body, Depends, File, Form, Query, UploadFile
from typing import Dict

from security import ErrorCode, error_response
from security.auth import User

# Auth helpers (mirrored — will be consolidated)
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from security import get_current_user

security_bearer = HTTPBearer(auto_error=False)


async def get_token_from_request(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)) -> str:
    if credentials:
        return credentials.credentials
    return None


async def require_authentication(token: str = Depends(get_token_from_request)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    return user


logger = logging.getLogger("routes.conversations")

UPLOAD_DIR = "temp_audio"

router = APIRouter()


@router.post("/conversations/export")
async def export_conversation(body: dict, user: User = Depends(require_authentication)):
    """Export conversation in various formats (markdown, json, txt)."""
    messages = body.get("messages", [])
    fmt = body.get("format", "markdown")
    include_meta = body.get("includeMetadata", True)
    include_timestamps = body.get("includeTimestamps", False)
    metadata = body.get("metadata", {})

    if not messages:
        return error_response(ErrorCode.VALIDATION_ERROR, "No messages to export", status_code=400)

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    date_str = time.strftime("%Y-%m-%d")

    if fmt == "json":
        export_data = {
            "version": "1.0",
            "exported_at": timestamp,
            "messages": messages
        }
        if include_meta:
            export_data["metadata"] = metadata
        return {"content": json.dumps(export_data, indent=2), "filename": f"conversation-{date_str}.json"}

    elif fmt == "markdown":
        lines = []
        if include_meta:
            lines.append(f"# Conversation Export")
            lines.append(f"**Date:** {timestamp}")
            if metadata.get("mode"):
                lines.append(f"**Mode:** {metadata['mode']}")
            if metadata.get("model"):
                lines.append(f"**Model:** {metadata['model']}")
            lines.append("")

        for msg in messages:
            role = msg.get("role", "unknown")
            text = msg.get("text", "")
            ts = msg.get("timestamp", "")

            header = "## You" if role == "user" else "## AI"
            if include_timestamps and ts:
                ts_str = time.strftime("%H:%M:%S", time.localtime(ts / 1000)) if isinstance(ts, (int, float)) else str(ts)
                header += f" ({ts_str})"

            lines.append(header)
            lines.append("")
            lines.append(text)
            lines.append("")

        content = "\n".join(lines)
        return {"content": content, "filename": f"conversation-{date_str}.md"}

    else:  # txt
        lines = []
        if include_meta:
            lines.append(f"Conversation Export - {timestamp}")
            lines.append("=" * 50)
            lines.append("")

        for msg in messages:
            role = "You" if msg.get("role") == "user" else "AI"
            text = msg.get("text", "")
            ts = msg.get("timestamp", "")

            prefix = f"[{role}]"
            if include_timestamps and ts:
                ts_str = time.strftime("%H:%M:%S", time.localtime(ts / 1000)) if isinstance(ts, (int, float)) else str(ts)
                prefix += f" {ts_str}"

            lines.append(f"{prefix}: {text}")
            lines.append("")

        content = "\n".join(lines)
        return {"content": content, "filename": f"conversation-{date_str}.txt"}


@router.post("/conversations/import")
async def import_conversations(file: UploadFile = File(...), user: User = Depends(require_authentication)):
    """Import conversations from JSON file."""
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))

        if not isinstance(data, dict) or "messages" not in data:
            return error_response(ErrorCode.INVALID_FORMAT, "Invalid format - expected JSON with 'messages' array", status_code=422)

        messages = data.get("messages", [])
        metadata = data.get("metadata", {})

        return {
            "success": True,
            "messages": messages,
            "metadata": metadata,
            "count": len(messages)
        }
    except json.JSONDecodeError as e:
        return error_response(ErrorCode.INVALID_FORMAT, "Invalid JSON format", status_code=422)
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), user: User = Depends(require_authentication)):
    """Upload a document for RAG context retrieval."""
    from document_store import get_document_store

    # SECURITY: Sanitize filename to prevent path traversal
    safe_filename = os.path.basename(file.filename)
    if not safe_filename or "/" in file.filename or "\\" in file.filename or ".." in file.filename:
        return error_response(ErrorCode.VALIDATION_ERROR, "Invalid filename", status_code=400)

    temp_path = os.path.join(UPLOAD_DIR, safe_filename)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        doc_store = get_document_store()
        result = doc_store.add_document(temp_path)

        try:
            os.remove(temp_path)
        except OSError:
            pass

        return result
    except Exception as e:
        logger.error("Document upload failed: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/documents")
async def list_documents(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    """List all uploaded documents with pagination."""
    from document_store import get_document_store
    doc_store = get_document_store()
    all_docs = doc_store.list_documents()
    total = len(all_docs)
    return {
        "documents": all_docs[offset:offset + limit],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user: User = Depends(require_authentication)):
    """Delete a document from the store."""
    from document_store import get_document_store
    doc_store = get_document_store()
    success = doc_store.delete_document(doc_id)
    return {"success": success}


@router.post("/documents/retrieve")
async def retrieve_document_context(query: str = Form(...), top_k: int = Form(5)):
    """Retrieve relevant document context for a query."""
    from document_store import get_document_store
    doc_store = get_document_store()
    results = doc_store.retrieve_context(query, top_k)
    return {"results": results}