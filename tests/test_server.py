"""Tests for clawplay.server — self-hosted web UI."""

from __future__ import annotations

import json

import pytest

try:
    from fastapi.testclient import TestClient

    from clawplay.server import create_app

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


pytestmark = pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed")


def test_health_endpoint() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "clawplay"
    assert body["version"] == "1.1.0"


def test_landing_page_renders() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "clawplay" in resp.text


def test_preview_route_returns_template_with_data() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/preview/worldcup/USA/Mexico")
    assert resp.status_code == 200
    assert "<title>" in resp.text
    assert 'id="clawplay-data"' in resp.text
    assert "worldcup" in resp.text


def test_live_route_injects_sport() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/live/nfl/Cowboys/Eagles")
    assert resp.status_code == 200
    assert "nfl" in resp.text
    assert "Cowboys" in resp.text


def test_recap_route_injects_data() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/recap/nba/Lakers/Celtics")
    assert resp.status_code == 200
    assert "Lakers" in resp.text
    assert "Celtics" in resp.text


def test_hub_route_renders() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/hub/dallas_cowboys")
    assert resp.status_code == 200
    assert "dallas_cowboys" in resp.text


def test_api_preview_returns_json() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/preview/worldcup/USA/Mexico")
    assert resp.status_code == 200
    body = resp.json()
    assert "payload" in body
    assert body["payload"]["sport"] == "worldcup"


def test_api_live_returns_json() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/live/nfl/Cowboys/Eagles")
    body = resp.json()
    assert body["payload"]["status"] == "LIVE"


def test_api_recap_returns_json() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/recap/nfl/Cowboys/Eagles")
    body = resp.json()
    assert body["payload"]["status"] == "FINAL"


def test_api_hub_returns_team_payload() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/hub/dallas_cowboys")
    body = resp.json()
    assert body["team"] == "dallas_cowboys"
    assert body["data"]["record"] == "8-4"


def test_template_data_includes_palette() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/preview/nfl/Cowboys/Eagles")
    # Find the injected <script id="clawplay-data"> block and parse it.
    marker = '<script id="clawplay-data" type="application/json">'
    start = resp.text.find(marker) + len(marker)
    end = resp.text.find("</script>", start)
    payload = json.loads(resp.text[start:end])
    assert "--palette-primary" in payload["palette"]
