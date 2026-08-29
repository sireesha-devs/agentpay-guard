from fastapi.testclient import TestClient

from backend.app.main import app


def test_fastapi_app_can_be_imported():
    assert app.title == "AgentPay Guard API"


def test_health_endpoint_returns_healthy_response():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
