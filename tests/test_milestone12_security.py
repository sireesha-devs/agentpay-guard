import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.security.rate_limit import rate_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def valid_payload() -> dict[str, object]:
    return {
        "transaction_id": "security-test-1",
        "buyer_id": "buyer-1",
        "quantity": 2,
        "max_budget": 1000.0,
        "currency": "INR",
        "minimum_refund_days": 7,
        "seller_id": "seller-1",
        "unit_price": 400.0,
        "seller_currency": "INR",
        "refund_days": 7,
        "terms": "Seven-day return policy",
    }


def test_missing_api_key_returns_401(client):
    response = client.post(
        "/transactions",
        json=valid_payload(),
    )

    assert response.status_code == 401


def test_invalid_api_key_returns_401(client):
    response = client.post(
        "/transactions",
        json=valid_payload(),
        headers={"X-API-Key": "invalid-key"},
    )

    assert response.status_code == 401


def test_buyer_api_key_is_authorized(client):
    response = client.post(
        "/transactions",
        json=valid_payload(),
        headers={"X-API-Key": "buyer-demo-key"},
    )

    assert response.status_code == 200


def test_admin_api_key_is_authorized(client):
    response = client.post(
        "/transactions",
        json=valid_payload(),
        headers={"X-API-Key": "admin-demo-key"},
    )

    assert response.status_code == 200


def test_seller_api_key_is_forbidden(client):
    response = client.post(
        "/transactions",
        json=valid_payload(),
        headers={"X-API-Key": "seller-demo-key"},
    )

    assert response.status_code == 403


def test_extra_payload_fields_are_rejected(client):
    payload = valid_payload()
    payload["malicious_extra_field"] = "unexpected"

    response = client.post(
        "/transactions",
        json=payload,
        headers={"X-API-Key": "buyer-demo-key"},
    )

    assert response.status_code == 422


def test_invalid_quantity_is_rejected(client):
    payload = valid_payload()
    payload["quantity"] = 0

    response = client.post(
        "/transactions",
        json=payload,
        headers={"X-API-Key": "buyer-demo-key"},
    )

    assert response.status_code == 422


def test_health_does_not_require_api_key(client):
    response = client.get("/health")

    assert response.status_code == 200


def test_rate_limit_returns_429(client):
    headers = {"X-API-Key": "buyer-demo-key"}

    for index in range(30):
        payload = valid_payload()
        payload["transaction_id"] = f"rate-limit-{index}"

        response = client.post(
            "/transactions",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 200

    payload = valid_payload()
    payload["transaction_id"] = "rate-limit-blocked"

    response = client.post(
        "/transactions",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 429