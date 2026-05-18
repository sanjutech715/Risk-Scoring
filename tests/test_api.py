from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_root_endpoint() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Summary & Risk Scoring API" in response.text
    assert "/docs" in response.text
    assert "/health" in response.text


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["version"] == "1.0.0"
    assert isinstance(payload["models_loaded"], bool)
