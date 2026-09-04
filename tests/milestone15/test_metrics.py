from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_metrics_endpoint_is_exposed():
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "agentpay_http_requests_total" in response.text
    assert "agentpay_http_request_duration_seconds" in response.text


def test_http_request_metrics_are_recorded():
    response = client.get("/health")

    assert response.status_code == 200

    metrics = client.get("/metrics")

    assert metrics.status_code == 200
    assert 'path="/health"' in metrics.text
    assert 'method="GET"' in metrics.text


def test_readiness_metrics_are_recorded():
    response = client.get("/readiness")

    assert response.status_code == 200

    metrics = client.get("/metrics")

    assert metrics.status_code == 200
    assert 'path="/readiness"' in metrics.text
      