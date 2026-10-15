from datetime import datetime, timezone
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from security.errors import ErrorCode, error_response


@pytest.mark.parametrize('status', [400, 401, 403, 404, 409, 413, 422, 429, 500, 502, 503])
def test_structured_errors_have_actual_http_status(status):
    app = FastAPI()
    @app.get('/failure')
    def failure():
        return error_response(ErrorCode.INTERNAL_ERROR, 'Synthetic failure', status_code=status)
    with TestClient(app) as client:
        result = client.get('/failure')
    assert result.status_code == status
    assert result.json() == {'error': {'code': ErrorCode.INTERNAL_ERROR, 'message': 'Synthetic failure'}}
    assert result.headers['content-type'] == 'application/json'


def test_error_details_encode_dates_and_uuids_and_preserve_extra_fields():
    app = FastAPI()
    @app.get('/models', response_model=dict)
    def models():
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, 'Unavailable', status_code=502,
            details={'at': datetime(2026, 1, 1, tzinfo=timezone.utc), 'id': UUID(int=1)},
            extra={'models': [], 'error': 'cannot replace structured error'})
    with TestClient(app) as client:
        result = client.get('/models')
    assert result.status_code == 502
    assert result.json()['models'] == []
    assert result.json()['error']['details'] == {'at': '2026-01-01T00:00:00+00:00', 'id': str(UUID(int=1))}
