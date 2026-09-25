"""Check cleanup on the existing event loop without starting the real app/database."""
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import pytest

@pytest.mark.asyncio
async def test_shutdown_awaits_database_on_running_event_loop(monkeypatch):
    import lib.http_client as clients
    close_http=AsyncMock(); close_sync=Mock()
    monkeypatch.setattr(clients,'close_client',close_http)
    monkeypatch.setattr(clients,'sync_client',SimpleNamespace(close=close_sync))
    tree=ast.parse((Path(__file__).parents[1]/'core/main.py').read_text())
    fn=next(node for node in tree.body if isinstance(node,ast.AsyncFunctionDef) and node.name=='shutdown_event')
    fn.decorator_list=[]
    close_db=AsyncMock()
    state=SimpleNamespace(use_autonomous=True)
    scope={'DATABASE_AVAILABLE':True,'close_database':close_db,'_state':state,'logger':Mock()}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'<shutdown>','exec'),scope)
    await scope['shutdown_event']()
    close_db.assert_awaited_once()
    close_http.assert_awaited_once()
    close_sync.assert_called_once()
    assert not state.use_autonomous
    # No import-time signal handler can bypass Uvicorn's awaited shutdown.
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='signal' and n.func.attr=='signal' for n in ast.walk(tree))
