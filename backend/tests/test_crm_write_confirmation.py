"""Never report a CRM write that the provider did not confirm."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from modules.crm.crm_real_integration import (
    CRMActivity, CRMConfig, CRMContact, CRMManager, CRMOperationUnavailable,
    HubSpotIntegration, SalesforceIntegration,
)


@pytest.fixture(params=[HubSpotIntegration, SalesforceIntegration])
def integration(request):
    adapter = request.param(CRMConfig(provider='synthetic'))
    adapter._api_client = object()
    adapter._sf = object()
    return adapter


@pytest.mark.asyncio
async def test_placeholder_writes_cannot_return_invented_identifiers(integration):
    contact = CRMContact(email='synthetic@example.invalid')
    activity = CRMActivity('meeting', datetime.now(timezone.utc), 'Synthetic notes')
    for method, args in ((integration.create_contact, (contact,)),
                         (integration.update_contact, ('synthetic-id', contact)),
                         (integration.log_activity, (activity,))):
        with pytest.raises(CRMOperationUnavailable):
            await method(*args)


@pytest.mark.asyncio
@pytest.mark.parametrize('existing', [None, {'id': 'synthetic-id'}])
@pytest.mark.parametrize('outcome', ['confirmed', 'empty', 'error', 'unavailable'])
async def test_sync_counts_only_confirmed_operations(integration, existing, outcome):
    integration.find_contact_by_email = AsyncMock(return_value=existing)
    error = (RuntimeError('synthetic-private-provider-detail') if outcome == 'error' else
             CRMOperationUnavailable('static unavailable') if outcome == 'unavailable' else None)
    operation = AsyncMock(return_value='provider-confirmed-id' if outcome == 'confirmed' else None,
                          side_effect=error)
    integration.create_contact = operation
    integration.update_contact = operation
    result = await integration.sync_contacts([CRMContact(email='synthetic@example.invalid')])
    assert result['total'] == 1
    assert result['created'] == int(outcome == 'confirmed' and existing is None)
    assert result['updated'] == int(outcome == 'confirmed' and existing is not None)
    assert result['failed'] == int(outcome != 'confirmed')
    assert 'synthetic-private-provider-detail' not in str(result)
    assert len(result['errors']) == int(outcome != 'confirmed')


@pytest.mark.asyncio
async def test_hubspot_client_object_is_not_proof_of_connectivity():
    adapter = HubSpotIntegration(CRMConfig(provider='hubspot'))
    adapter._api_client = object()
    assert await adapter.test_connection() is False


@pytest.mark.asyncio
async def test_meeting_sync_preserves_failed_contact_and_activity_results(integration):
    integration.find_contact_by_email = AsyncMock(return_value=None)
    manager = CRMManager()
    manager.integrations['synthetic'] = integration
    result = await manager.sync_meeting_participants('synthetic',
        [{'email': 'synthetic@example.invalid'}], {'summary': 'Synthetic meeting'})
    assert result['contacts_synced'] == result['activities_logged'] == 0
    assert len(result['errors']) == 2
