"""API integration tests."""

from fastapi.testclient import TestClient

from ai_os.api.app import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_endpoint() -> None:
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "counts" in data
    assert "provider_health" in data


def test_knowledge_documents() -> None:
    response = client.get("/api/v1/knowledge/documents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_providers_health() -> None:
    response = client.get("/api/v1/providers/health")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_models_list() -> None:
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_global_search() -> None:
    response = client.get("/api/v1/search", params={"q": "test"})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "test"
    assert "knowledge" in data


def test_import_presets() -> None:
    response = client.get("/api/v1/imports/presets")
    assert response.status_code == 200
    presets = response.json()
    assert any(p["id"] == "ai-os-repo" for p in presets)
