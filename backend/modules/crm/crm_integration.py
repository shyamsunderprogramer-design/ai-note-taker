"""
crm_integration.py - CRM Integration for AI Note Taker

Supports:
- Webhook-based CRM integration (generic)
- Salesforce OAuth and API
- HubSpot API
- Activity/task logging
- Contact matching
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
import requests

logger = logging.getLogger("crm")

# Storage path
DATA_DIR = Path(os.path.dirname(__file__)) / "data"
CRM_CONFIG_FILE = DATA_DIR / "crm_config.json"

# Ensure directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class CRMConfig:
    """Configuration for CRM integration."""
    enabled: bool = False
    provider: str = ""  # salesforce, hubspot, webhook
    webhook_url: Optional[str] = None
    api_key: Optional[str] = None
    oauth_token: Optional[str] = None
    instance_url: Optional[str] = None  # For Salesforce
    contact_matching: bool = True
    auto_log_conversations: bool = True
    log_format: str = "summary"  # summary, full, transcript

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "CRMConfig":
        return cls(**data)


class CRMIntegration:
    """Manages CRM integration."""

    def __init__(self):
        self.config = CRMConfig()
        self._load_config()

    def _load_config(self):
        """Load CRM configuration."""
        if CRM_CONFIG_FILE.exists():
            try:
                with open(CRM_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.config = CRMConfig.from_dict(data)
            except Exception as e:
                logger.warning("Failed to load CRM config: %s", str(e))

    def _save_config(self):
        """Save CRM configuration."""
        try:
            with open(CRM_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config.to_dict(), f, indent=2)
        except Exception as e:
            logger.error("Failed to save CRM config: %s", str(e))

    def configure(self, config: Dict) -> bool:
        """Update CRM configuration."""
        try:
            self.config = CRMConfig(**config)
            self._save_config()
            return True
        except Exception as e:
            logger.error("Failed to configure CRM: %s", str(e))
            return False

    def get_config(self) -> Dict:
        """Get current CRM configuration."""
        return self.config.to_dict()

    def _send_webhook(self, event_type: str, data: Dict) -> bool:
        """Send data to webhook URL."""
        if not self.config.webhook_url:
            logger.warning("No webhook URL configured")
            return False

        try:
            payload = {
                "event": event_type,
                "timestamp": time.time(),
                "data": data
            }

            headers = {"Content-Type": "application/json"}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"

            response = requests.post(
                self.config.webhook_url,
                json=payload,
                headers=headers,
                timeout=30
            )

            return response.status_code in (200, 201, 202)
        except Exception as e:
            logger.error("Webhook failed: %s", str(e))
            return False

    def _log_to_salesforce(self, event_type: str, data: Dict) -> bool:
        """Log activity to Salesforce."""
        if not self.config.oauth_token or not self.config.instance_url:
            logger.warning("Salesforce not authenticated")
            return False

        try:
            # Create a Task activity
            if event_type == "conversation_completed":
                task_data = {
                    "Subject": f"AI Note Taker: {data.get('title', 'Conversation')}",
                    "Description": self._format_conversation_description(data),
                    "Status": "Completed",
                    "Priority": "Normal"
                }

                headers = {
                    "Authorization": f"Bearer {self.config.oauth_token}",
                    "Content-Type": "application/json"
                }

                response = requests.post(
                    f"{self.config.instance_url}/services/data/v58.0/sobjects/Task",
                    json=task_data,
                    headers=headers,
                    timeout=30
                )

                return response.status_code == 201

            return True
        except Exception as e:
            logger.error("Salesforce API failed: %s", str(e))
            return False

    def _log_to_hubspot(self, event_type: str, data: Dict) -> bool:
        """Log activity to HubSpot."""
        if not self.config.api_key:
            logger.warning("HubSpot API key not configured")
            return False

        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }

            if event_type == "conversation_completed":
                # Create engagement
                engagement_data = {
                    "engagement": {
                        "type": "NOTE",
                        "timestamp": int(time.time() * 1000)
                    },
                    "metadata": {
                        "body": self._format_conversation_description(data)
                    }
                }

                response = requests.post(
                    "https://api.hubapi.com/engagements/v1/engagements",
                    json=engagement_data,
                    headers=headers,
                    timeout=30
                )

                return response.status_code == 200

            return True
        except Exception as e:
            logger.error("HubSpot API failed: %s", str(e))
            return False

    def _format_conversation_description(self, data: Dict) -> str:
        """Format conversation data for CRM."""
        fmt = self.config.log_format

        if fmt == "transcript":
            lines = ["AI Note Taker Transcript"]
            lines.append(f"Date: {data.get('date', 'Unknown')}")
            lines.append("")
            for msg in data.get("messages", []):
                role = "User" if msg.get("role") == "user" else "AI"
                lines.append(f"{role}: {msg.get('text', '')}")
            return "\n".join(lines)

        elif fmt == "full":
            lines = ["AI Note Taker Conversation"]
            lines.append(f"Title: {data.get('title', 'Untitled')}")
            lines.append(f"Date: {data.get('date', 'Unknown')}")
            lines.append(f"Messages: {len(data.get('messages', []))}")
            lines.append("")
            lines.append("Summary:")
            for msg in data.get("messages", []):
                if msg.get("role") == "user":
                    lines.append(f"Q: {msg.get('text', '')}")
                else:
                    lines.append(f"A: {msg.get('text', '')[:200]}...")
            return "\n".join(lines)

        else:  # summary
            user_msgs = [m for m in data.get("messages", []) if m.get("role") == "user"]
            return f"AI Note Taker conversation: {data.get('title', 'Untitled')}\n" \
                   f"Date: {data.get('date', 'Unknown')}\n" \
                   f"Messages: {len(data.get('messages', []))}\n" \
                   f"Questions asked: {len(user_msgs)}"

    def log_event(self, event_type: str, data: Dict) -> bool:
        """Log an event to the configured CRM."""
        if not self.config.enabled:
            return False

        if self.config.provider == "webhook":
            return self._send_webhook(event_type, data)
        elif self.config.provider == "salesforce":
            return self._log_to_salesforce(event_type, data)
        elif self.config.provider == "hubspot":
            return self._log_to_hubspot(event_type, data)
        else:
            logger.warning(f"Unknown CRM provider: {self.config.provider}")
            return False

    def test_connection(self) -> Dict:
        """Test the CRM connection."""
        if not self.config.enabled:
            return {"status": "disabled", "message": "CRM integration not enabled"}

        try:
            if self.config.provider == "webhook":
                if not self.config.webhook_url:
                    return {"status": "error", "message": "Webhook URL not configured"}
                # Try a simple ping
                response = requests.post(
                    self.config.webhook_url,
                    json={"test": True},
                    timeout=10
                )
                if response.status_code in (200, 201, 202):
                    return {"status": "ok", "message": "Webhook reachable"}
                else:
                    return {"status": "warning", "message": f"Unexpected status: {response.status_code}"}

            elif self.config.provider == "salesforce":
                if not self.config.oauth_token:
                    return {"status": "error", "message": "Not authenticated with Salesforce"}
                headers = {"Authorization": f"Bearer {self.config.oauth_token}"}
                response = requests.get(
                    f"{self.config.instance_url}/services/data/v58.0/limits",
                    headers=headers,
                    timeout=10
                )
                if response.status_code == 200:
                    return {"status": "ok", "message": "Salesforce connection active"}
                elif response.status_code == 401:
                    return {"status": "error", "message": "Salesforce token expired"}
                else:
                    return {"status": "warning", "message": f"Unexpected status: {response.status_code}"}

            elif self.config.provider == "hubspot":
                if not self.config.api_key:
                    return {"status": "error", "message": "HubSpot API key not configured"}
                headers = {"Authorization": f"Bearer {self.config.api_key}"}
                response = requests.get(
                    "https://api.hubapi.com/integrations/v1/me",
                    headers=headers,
                    timeout=10
                )
                if response.status_code == 200:
                    return {"status": "ok", "message": "HubSpot connection active"}
                elif response.status_code == 401:
                    return {"status": "error", "message": "Invalid HubSpot API key"}
                else:
                    return {"status": "warning", "message": f"Unexpected status: {response.status_code}"}

            return {"status": "unknown", "message": "Unknown provider"}

        except Exception as e:
            return {"status": "error", "message": "An internal error occurred"}


# Global CRM instance
_crm_instance = None


def get_crm() -> CRMIntegration:
    """Get the global CRM instance."""
    global _crm_instance
    if _crm_instance is None:
        _crm_instance = CRMIntegration()
    return _crm_instance
