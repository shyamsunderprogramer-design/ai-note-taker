"""Shared helpers for integration route modules.

Provides unified config retrieval and persistence for all integrations,
with automatic encryption of secrets at rest.
"""

import logging
from typing import Optional, Dict, Any

from database import IntegrationConfigRepository

logger = logging.getLogger("routes.integration_helpers")


async def get_integration_config(user_id: str, integration_type: str) -> Dict[str, Any]:
    """Get merged config + decrypted secrets for an integration.

    Returns:
        dict with keys: connected (bool), enabled (bool), config (dict), secrets (dict),
        last_sync_at, sync_errors
    """
    record = await IntegrationConfigRepository.get_by_user_and_type(user_id, integration_type)
    if not record:
        return {
            "connected": False,
            "enabled": False,
            "config": {},
            "secrets": {},
            "last_sync_at": None,
            "sync_errors": [],
        }
    return {
        "connected": record.enabled,
        "enabled": record.enabled,
        "config": record.config or {},
        "secrets": IntegrationConfigRepository.decrypt_secrets_for_record(record),
        "last_sync_at": getattr(record, 'last_sync_at', None),
        "sync_errors": getattr(record, 'sync_errors', []) or [],
    }


async def save_integration_config(
    user_id: str,
    integration_type: str,
    config: Optional[dict] = None,
    secrets: Optional[dict] = None,
    enabled: bool = True,
) -> bool:
    """Save integration config and secrets (secrets encrypted at rest).

    Returns True on success.
    """
    record = await IntegrationConfigRepository.upsert(
        user_id=user_id,
        integration_type=integration_type,
        config=config,
        secrets=secrets,
        enabled=enabled,
    )
    if record:
        logger.info("[IntegrationHelpers] Saved config for %s/%s", integration_type, user_id)
    else:
        logger.error("[IntegrationHelpers] Failed to save config for %s/%s", integration_type, user_id)
    return record is not None


async def delete_integration_config(user_id: str, integration_type: str) -> bool:
    """Delete integration config for a user.

    Returns True on success.
    """
    result = await IntegrationConfigRepository.delete(user_id, integration_type)
    if result:
        logger.info("[IntegrationHelpers] Deleted config for %s/%s", integration_type, user_id)
    return result