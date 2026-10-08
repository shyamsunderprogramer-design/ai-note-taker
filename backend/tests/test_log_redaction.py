import logging
from lib.log_redaction import CredentialFilter


def test_access_log_formats_arguments_before_redacting_websocket_credentials():
    record = logging.LogRecord('uvicorn.access', logging.INFO, '', 0,
        '%s - "%s %s HTTP/%s" %s', ('local', 'GET', '/ws/transcribe?token=private-token&source=system', '1.1', 101), None)
    assert CredentialFilter().filter(record)
    assert 'private-token' not in record.getMessage()
    assert 'source=system' in record.getMessage()
    assert '101' in record.getMessage()


def test_access_log_redacts_bearer_and_jwt_and_preserves_operational_error():
    record = logging.LogRecord('uvicorn.access', logging.ERROR, '', 0,
        'HTTP 401 Bearer private-key eyJheader.payload.signature api /?api_key=private-secret', (), None)
    CredentialFilter().filter(record)
    assert 'HTTP 401' in record.getMessage()
    assert all(secret not in record.getMessage() for secret in ('private-key', 'private-secret', 'eyJheader'))
