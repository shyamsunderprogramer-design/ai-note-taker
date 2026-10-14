"""CRM adapter interfaces, connection status, and confirmed-write accounting.

Legacy provider writes are unavailable until backed by actual API requests;
callers receive explicit failures instead of fabricated contact/activity IDs.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("crm_integration")

# Try importing CRM SDKs
try:
    from hubspot import HubSpotApi
    HAS_HUBSPOT = True
except ImportError:
    HAS_HUBSPOT = False
    logger.warning("[CRM] HubSpot SDK not available")

try:
    from simple_salesforce import Salesforce
    HAS_SALESFORCE = False  # Set to True when simple_salesforce is installed
except ImportError:
    HAS_SALESFORCE = False
    logger.warning("[CRM] Salesforce SDK not available")


@dataclass
class CRMContact:
    """Unified contact representation"""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None  # 'meeting', 'manual', 'import'
    last_interaction: Optional[datetime] = None
    notes: Optional[str] = None
    custom_fields: Dict = None

    def __post_init__(self):
        if self.custom_fields is None:
            self.custom_fields = {}


@dataclass
class CRMActivity:
    """Unified activity representation"""
    activity_type: str  # 'meeting', 'call', 'email', 'note'
    timestamp: datetime
    description: str
    contact_email: Optional[str] = None
    contact_id: Optional[str] = None
    duration_minutes: Optional[int] = None
    outcome: Optional[str] = None  # 'completed', 'no_show', 'rescheduled'
    notes: Optional[str] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class CRMConfig:
    """CRM configuration"""
    provider: str  # 'hubspot' or 'salesforce'
    enabled: bool = False
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    instance_url: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    sync_frequency: str = "hourly"  # 'realtime', 'hourly', 'daily'
    last_sync_at: Optional[datetime] = None
    sync_errors: List[str] = None

    def __post_init__(self):
        if self.sync_errors is None:
            self.sync_errors = []


class CRMOperationUnavailable(RuntimeError):
    """An adapter operation has no implemented provider request."""


class BaseCRMIntegration:
    """Base class for CRM integrations"""

    def __init__(self, config: CRMConfig):
        self.config = config
        self._client = None

    async def initialize(self) -> bool:
        """Initialize CRM client"""
        raise NotImplementedError

    async def test_connection(self) -> bool:
        """Test CRM connection"""
        raise NotImplementedError

    async def create_contact(self, contact: CRMContact) -> Optional[str]:
        """Create or update contact, returns contact ID"""
        raise NotImplementedError

    async def update_contact(self, contact_id: str, contact: CRMContact) -> bool:
        """Update existing contact"""
        raise NotImplementedError

    async def find_contact_by_email(self, email: str) -> Optional[Dict]:
        """Find contact by email"""
        raise NotImplementedError

    async def log_activity(self, activity: CRMActivity) -> Optional[str]:
        """Log activity, returns activity ID"""
        raise NotImplementedError

    async def sync_contacts(self, contacts: List[CRMContact]) -> Dict[str, Any]:
        """Count only writes confirmed by the provider."""
        results = {"total": len(contacts), "created": 0, "updated": 0,
                   "failed": 0, "errors": []}
        for contact in contacts:
            try:
                existing = await self.find_contact_by_email(contact.email)
                if existing:
                    confirmed = await self.update_contact(existing.get("id") or existing.get("Id"), contact)
                    operation = "updated"
                else:
                    confirmed = await self.create_contact(contact)
                    operation = "created"
                if not confirmed:
                    raise RuntimeError("CRM provider did not confirm the write")
                results[operation] += 1
            except CRMOperationUnavailable:
                results["failed"] += 1
                results["errors"].append("CRM writes are not implemented for this adapter")
            except Exception:
                results["failed"] += 1
                results["errors"].append("CRM provider did not confirm the write")
        return results


class HubSpotIntegration(BaseCRMIntegration):
    """
    HubSpot CRM Integration
    Uses HubSpot API v3 for contacts, engagements, and deals
    """

    def __init__(self, config: CRMConfig):
        super().__init__(config)
        self._api_client = None

    async def initialize(self) -> bool:
        """Initialize HubSpot API client"""
        if not HAS_HUBSPOT:
            logger.error("[HubSpot] SDK not available. Install: pip install hubspot-api-client")
            return False

        if not self.config.access_token:
            logger.error("[HubSpot] No access token configured")
            return False

        try:
            # Initialize HubSpot API client
            self._api_client = HubSpotApi(access_token=self.config.access_token)
            logger.info("[HubSpot] Client initialized")
            return await self.test_connection()
        except Exception as e:
            logger.error("[HubSpot] Initialization failed: %s", str(e))
            return False

    async def test_connection(self) -> bool:
        """Client construction alone does not verify a remote connection."""
        logger.warning("[HubSpot] Connection verification is not implemented")
        return False

    async def create_contact(self, contact: CRMContact) -> Optional[str]:
        """No provider write is implemented; never fabricate a contact ID."""
        raise CRMOperationUnavailable("HubSpot contact creation is unavailable")

    async def find_contact_by_email(self, email: str) -> Optional[Dict]:
        """Find contact by email in HubSpot"""
        if not self._api_client:
            return None

        # Would use HubSpot API to search
        # Contact lookup is not implemented in this legacy adapter.
        return None

    async def log_activity(self, activity: CRMActivity) -> Optional[str]:
        """No provider write is implemented; never fabricate an activity ID."""
        raise CRMOperationUnavailable("HubSpot activity logging is unavailable")


    async def update_contact(self, contact_id: str, contact: CRMContact) -> bool:
        """An unimplemented update cannot be reported as successful."""
        raise CRMOperationUnavailable("HubSpot contact updates are unavailable")


class SalesforceIntegration(BaseCRMIntegration):
    """
    Salesforce CRM Integration
    Uses Salesforce REST API for leads, contacts, and tasks
    """

    def __init__(self, config: CRMConfig):
        super().__init__(config)
        self._sf = None

    async def initialize(self) -> bool:
        """Initialize Salesforce client"""
        if not HAS_SALESFORCE:
            logger.error("[Salesforce] SDK not available. Install: pip install simple-salesforce")
            return False

        if not all([self.config.access_token, self.config.instance_url]):
            logger.error("[Salesforce] Missing credentials")
            return False

        try:
            # Initialize Salesforce client
            self._sf = Salesforce(
                instance_url=self.config.instance_url,
                session_id=self.config.access_token
            )
            logger.info("[Salesforce] Client initialized")
            return True
        except Exception as e:
            logger.error("[Salesforce] Initialization failed: %s", str(e))
            return False

    async def test_connection(self) -> bool:
        """Test Salesforce connection"""
        if not self._sf:
            return False

        try:
            # Query limits to test connection
            self._sf.limits()
            logger.info("[Salesforce] Connection test successful")
            return True
        except Exception as e:
            logger.error("[Salesforce] Connection test failed: %s", str(e))
            return False

    async def create_contact(self, contact: CRMContact) -> Optional[str]:
        """No provider write is implemented; never fabricate a contact ID."""
        raise CRMOperationUnavailable("Salesforce contact creation is unavailable")

    async def find_contact_by_email(self, email: str) -> Optional[Dict]:
        """Find contact or lead by email in Salesforce"""
        if not self._sf:
            return None

        try:
            # SECURITY: Escape email to prevent SOQL injection
            from simple_salesforce.format import format_soql

            # Query Contacts
            result = self._sf.query(format_soql("SELECT Id, Name, Email FROM Contact WHERE Email = {}", email or ""))
            if result.get("totalSize", 0) > 0:
                return result["records"][0]

            # Query Leads if not found in Contacts
            result = self._sf.query(format_soql("SELECT Id, Name, Email FROM Lead WHERE Email = {}", email or ""))
            if result.get("totalSize", 0) > 0:
                return result["records"][0]

            return None
        except Exception as e:
            logger.error("[Salesforce] Find contact failed: %s", str(e))
            return None

    async def log_activity(self, activity: CRMActivity) -> Optional[str]:
        """No provider write is implemented; never fabricate an activity ID."""
        raise CRMOperationUnavailable("Salesforce activity logging is unavailable")


    async def update_contact(self, contact_id: str, contact: CRMContact) -> bool:
        """An unimplemented update cannot be reported as successful."""
        raise CRMOperationUnavailable("Salesforce contact updates are unavailable")


class CRMManager:
    """
    Unified CRM manager that handles multiple CRM integrations.
    Provides a single interface for CRM operations.
    """

    def __init__(self):
        self.integrations: Dict[str, BaseCRMIntegration] = {}
        self._configs: Dict[str, CRMConfig] = {}

    def add_integration(self, name: str, config: CRMConfig) -> bool:
        """Add and initialize a CRM integration"""
        if config.provider == "hubspot":
            integration = HubSpotIntegration(config)
        elif config.provider == "salesforce":
            integration = SalesforceIntegration(config)
        else:
            logger.error(f"[CRM] Unknown provider: {config.provider}")
            return False

        self.integrations[name] = integration
        self._configs[name] = config
        return True

    async def initialize(self, name: str) -> bool:
        """Initialize a specific integration"""
        if name not in self.integrations:
            return False
        return await self.integrations[name].initialize()

    async def sync_meeting_participants(self, integration_name: str,
                                        participants: List[Dict],
                                        meeting_data: Dict) -> Dict[str, Any]:
        """
        Sync meeting participants to CRM.
        Creates/updates contacts and logs the meeting activity.
        """
        if integration_name not in self.integrations:
            return {"error": f"Integration not found: {integration_name}"}

        integration = self.integrations[integration_name]
        results = {
            "contacts_synced": 0,
            "activities_logged": 0,
            "errors": []
        }

        # Convert participants to CRM contacts
        contacts = []
        for participant in participants:
            contact = CRMContact(
                email=participant.get("email"),
                first_name=participant.get("first_name"),
                last_name=participant.get("last_name"),
                company=participant.get("company"),
                job_title=participant.get("job_title"),
                source="meeting"
            )
            contacts.append(contact)

        # Sync contacts
        sync_result = await integration.sync_contacts(contacts)
        results["contacts_synced"] = sync_result.get("created", 0) + sync_result.get("updated", 0)
        results["errors"].extend(sync_result.get("errors", []))

        # Log meeting activity for each participant
        for contact in contacts:
            activity = CRMActivity(
                activity_type="meeting",
                timestamp=meeting_data.get("started_at", datetime.now()),
                description=meeting_data.get("summary", "Interview meeting"),
                contact_email=contact.email,
                duration_minutes=meeting_data.get("duration_minutes"),
                outcome="completed",
                notes=meeting_data.get("notes", "")
            )

            try:
                activity_id = await integration.log_activity(activity)
                if activity_id:
                    results["activities_logged"] += 1
                else:
                    results["errors"].append("CRM provider did not confirm activity logging")
            except CRMOperationUnavailable:
                results["errors"].append("CRM activity logging is not implemented for this adapter")
            except Exception:
                results["errors"].append("CRM provider did not confirm activity logging")

        return results

    async def get_sync_status(self, integration_name: str) -> Dict[str, Any]:
        """Get sync status for an integration"""
        if integration_name not in self.integrations:
            return {"error": f"Integration not found: {integration_name}"}

        config = self._configs.get(integration_name)
        integration = self.integrations[integration_name]

        return {
            "provider": config.provider,
            "enabled": config.enabled,
            "last_sync_at": config.last_sync_at.isoformat() if config.last_sync_at else None,
            "sync_errors": len(config.sync_errors),
            "connected": await integration.test_connection()
        }


# Global CRM manager instance
crm_manager = CRMManager()


# API Functions
def create_crm_config(provider: str, credentials: Dict) -> CRMConfig:
    """Create CRM configuration from credentials"""
    return CRMConfig(
        provider=provider,
        enabled=True,
        access_token=credentials.get("access_token"),
        refresh_token=credentials.get("refresh_token"),
        instance_url=credentials.get("instance_url"),
        client_id=credentials.get("client_id"),
        client_secret=credentials.get("client_secret"),
        sync_frequency=credentials.get("sync_frequency", "hourly")
    )


async def initialize_crm_integration(name: str, config: CRMConfig) -> bool:
    """Initialize a CRM integration"""
    crm_manager.add_integration(name, config)
    return await crm_manager.initialize(name)


async def sync_contacts_to_crm(integration_name: str, contacts: List[CRMContact]) -> Dict[str, Any]:
    """Sync contacts to CRM"""
    if integration_name not in crm_manager.integrations:
        return {"error": "Integration not found"}
    return await crm_manager.integrations[integration_name].sync_contacts(contacts)


def get_crm_status() -> Dict[str, Any]:
    """Get overall CRM status"""
    return {
        "hubspot_available": HAS_HUBSPOT,
        "salesforce_available": HAS_SALESFORCE,
        "configured_integrations": list(crm_manager.integrations.keys()),
    }


__all__ = [
    "CRMContact",
    "CRMActivity",
    "CRMConfig",
    "BaseCRMIntegration",
    "HubSpotIntegration",
    "SalesforceIntegration",
    "CRMManager",
    "crm_manager",
    "create_crm_config",
    "initialize_crm_integration",
    "sync_contacts_to_crm",
    "get_crm_status",
]
