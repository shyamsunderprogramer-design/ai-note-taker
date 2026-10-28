"""Audit events must use the database instance initialized by the app."""
import pytest
from security.audit import AuditEvent, _write_to_database, get_audit_log_from_db


@pytest.mark.asyncio
async def test_audit_round_trip_uses_initialized_database(tmp_db):
    event = AuditEvent(timestamp='2026-09-27T00:00:00Z', event_type='qa_round_trip',
                       actor='qa-user', action='verify', resource='test', details={'isolated': True})
    assert await _write_to_database(event) is True
    entries = await get_audit_log_from_db(action='qa_round_trip')
    assert len(entries) == 1
    assert entries[0]['details']['actor'] == 'qa-user'
    assert entries[0]['details']['isolated'] is True
