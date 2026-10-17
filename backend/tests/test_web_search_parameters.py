"""Search input remains query data on the fixed provider endpoint."""
import ast
import logging
import os
import time
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI, Query
from fastapi.testclient import TestClient


@pytest.fixture(params=["core/main.py", "routes/ai.py"])
def search_client(request, monkeypatch):
    # Load both copies without starting databases, voice models or the live app.
    from lib import http_client

    tree = ast.parse((Path(__file__).parents[1] / request.param).read_text())
    endpoint = next(node for node in tree.body
                    if isinstance(node, ast.AsyncFunctionDef) and node.name == "web_search")
    endpoint.decorator_list = []
    requests = []

    def get(url, **kwargs):
        outgoing = httpx.Request("GET", url, params=kwargs["params"], headers=kwargs["headers"])
        requests.append(outgoing)
        return httpx.Response(200, request=outgoing, json={"web": {"results": [
            {"title": "Example", "url": "https://example.com", "description": "Result"}
        ]}})

    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.setenv("BRAVE_API_KEY", "synthetic-test-key")
    monkeypatch.setattr(http_client.sync_client, "get", get)
    scope = {"Query": Query, "os": os, "time": time,
             "logger": logging.getLogger(__name__), "sync_client": http_client.sync_client}
    exec(compile(ast.Module(body=[endpoint], type_ignores=[]), request.param, "exec"), scope)
    app = FastAPI()
    app.get("/search/web")(scope["web_search"])
    with TestClient(app) as client:
        yield client, requests


@pytest.mark.parametrize("query", [
    "Kubernetes autoscaling",
    "https://169.254.169.254/latest/meta-data/?q=override&count=100#fragment",
    "//attacker.example/@localhost\\path?new=value\r\nX-Injected: yes",
    "C++ & café / CI/CD",
])
def test_search_data_cannot_change_provider_url(search_client, query):
    client, requests = search_client
    response = client.get("/search/web", params={"query": query, "limit": 3})
    assert response.status_code == 200
    assert response.json()["query"] == query
    assert response.json()["results"][0]["title"] == "Example"
    assert len(requests) == 1
    outgoing = requests[0]
    assert outgoing.url.scheme == "https"
    assert outgoing.url.host == "api.search.brave.com"
    assert outgoing.url.path == "/res/v1/web/search"
    assert not outgoing.url.fragment
    assert outgoing.url.params.multi_items() == [("q", query), ("count", "3")]
    assert "X-Injected" not in outgoing.headers


@pytest.mark.parametrize("limit", [-1, 0, 21])
def test_invalid_result_limit_never_contacts_provider(search_client, limit):
    client, requests = search_client
    response = client.get("/search/web", params={"query": "question", "limit": limit})
    assert response.status_code == 422
    assert requests == []
