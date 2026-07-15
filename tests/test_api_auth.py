"""Regression: state-changing API routes require AI_OS_API_KEY when set."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ai_os.api.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    key = "test-security-key-do-not-use-in-prod"
    monkeypatch.setenv("AI_OS_API_KEY", key)
    return key


class TestWriteRouteAuth:
    def test_health_remains_public(self, client: TestClient, api_key: str) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert "test-security-key" not in response.text

    def test_dashboard_remains_public(self, client: TestClient, api_key: str) -> None:
        response = client.get("/api/v1/dashboard")
        assert response.status_code == 200
        assert api_key not in response.text

    @pytest.mark.parametrize(
        "method,path,kwargs",
        [
            (
                "post",
                "/api/v1/imports/upload",
                {"data": {"preset_id": "markdown-notes"}, "files": [("files", ("a.md", b"# a", "text/markdown"))]},
            ),
            (
                "post",
                "/api/v1/workflows/morning-briefing/run",
                {"json": {"inputs": {}}},
            ),
            ("post", "/api/v1/automations/morning-briefing/run", {}),
            ("post", "/api/v1/decisions", {"json": {"question": "probe?"}}),
            ("post", "/api/v1/knowledge/reindex", {}),
        ],
    )
    def test_unauthenticated_write_rejected(
        self,
        client: TestClient,
        api_key: str,
        method: str,
        path: str,
        kwargs: dict,
    ) -> None:
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 401, f"{path} returned {response.status_code}"
        assert api_key not in response.text

    def test_x_api_key_accepted_for_reindex(
        self, client: TestClient, api_key: str
    ) -> None:
        with patch(
            "ai_os.api.routers.knowledge.MaintenanceService.ensure_search_indexes"
        ):
            response = client.post(
                "/api/v1/knowledge/reindex",
                headers={"X-API-Key": api_key},
            )
        assert response.status_code == 200
        assert api_key not in response.text

    def test_bearer_accepted_for_reindex(
        self, client: TestClient, api_key: str
    ) -> None:
        with patch(
            "ai_os.api.routers.knowledge.MaintenanceService.ensure_search_indexes"
        ):
            response = client.post(
                "/api/v1/knowledge/reindex",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        assert response.status_code == 200

    def test_malformed_key_rejected(self, client: TestClient, api_key: str) -> None:
        response = client.post(
            "/api/v1/knowledge/reindex",
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401

    def test_missing_key_rejected(self, client: TestClient, api_key: str) -> None:
        response = client.post("/api/v1/knowledge/reindex")
        assert response.status_code == 401

    def test_unauthenticated_workflow_run_rejected(
        self, client: TestClient, api_key: str
    ) -> None:
        """Exact regression for production probe path."""
        response = client.post(
            "/api/v1/workflows/morning-briefing/run",
            json={"inputs": {}},
        )
        assert response.status_code == 401

    def test_unauthenticated_automation_run_rejected(
        self, client: TestClient, api_key: str
    ) -> None:
        response = client.post("/api/v1/automations/morning-briefing/run")
        assert response.status_code == 401

    def test_unauthenticated_decisions_rejected(
        self, client: TestClient, api_key: str
    ) -> None:
        response = client.post("/api/v1/decisions", json={"question": "x?"})
        assert response.status_code == 401

    def test_unauthenticated_upload_rejected(
        self, client: TestClient, api_key: str
    ) -> None:
        response = client.post(
            "/api/v1/imports/upload",
            data={"preset_id": "markdown-notes"},
            files=[("files", ("a.md", b"# a", "text/markdown"))],
        )
        assert response.status_code == 401
