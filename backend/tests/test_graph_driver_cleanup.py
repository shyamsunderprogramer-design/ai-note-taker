"""Failed optional graph connections must release resources before retrying."""
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from modules.ai import cognitive_graph as graph


@pytest.fixture
def driver(monkeypatch):
    monkeypatch.setattr(graph, '_driver', None)
    monkeypatch.setenv('NEO4J_PASSWORD', 'synthetic-private-password')
    candidate = MagicMock()
    factory = MagicMock(return_value=candidate)
    monkeypatch.setitem(sys.modules, 'neo4j', SimpleNamespace(GraphDatabase=SimpleNamespace(driver=factory)))
    return candidate, factory


def test_successful_graph_connection_is_reused(driver):
    candidate, factory = driver
    assert graph.get_driver() is candidate
    assert graph.get_driver() is candidate
    factory.assert_called_once()
    candidate.close.assert_not_called()


@pytest.mark.parametrize('failure', ['session', 'query', 'close'])
def test_failed_graph_connection_is_closed_and_not_cached(driver, failure, caplog):
    candidate, factory = driver
    if failure == 'session':
        candidate.session.return_value.__enter__.side_effect = RuntimeError('synthetic-private-host')
    else:
        candidate.session.return_value.__enter__.return_value.run.side_effect = RuntimeError('synthetic-private-host')
    if failure == 'close':
        candidate.close.side_effect = RuntimeError('synthetic-private-close-error')
    assert graph.get_driver() is None
    candidate.close.assert_called_once()
    assert graph._driver is None
    assert graph.get_driver() is None
    assert factory.call_count == 2
    assert 'synthetic-private' not in caplog.text
