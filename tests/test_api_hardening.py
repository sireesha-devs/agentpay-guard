import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(
    app,
    headers={"X-API-Key": "buyer-demo-key"},
)


def valid_payload() -> dict[str, object]:
    return {
        "transaction_id": "hardened-transaction-1",
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


def test_valid_transaction_still_returns_200(client):
    response = client.post("/transactions", json=valid_payload())

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("transaction_id", ""),
        ("buyer_id", ""),
        ("seller_id", ""),
        ("quantity", 0),
        ("max_budget", -1.0),
        ("minimum_refund_days", -1),
        ("unit_price", 0),
        ("refund_days", -1),
        ("max_rounds", 0),
        ("currency", ""),
        ("seller_currency", ""),
        ("terms", ""),
    ],
)
def test_invalid_transaction_fields_return_422(client, field, value):
    payload = valid_payload()
    payload[field] = value

    response = client.post("/transactions", json=payload)

    assert response.status_code == 422


def test_over_budget_transaction_keeps_business_outcome(client):
    payload = valid_payload()
    payload["unit_price"] = 600.0

    response = client.post("/transactions", json=payload)

    assert response.status_code == 200
    assert response.json()["negotiation_status"] == "REJECTED"
    assert response.json()["payment_status"] == "failed"


def test_currency_mismatch_reaches_policy_and_is_not_captured(client):
    payload = valid_payload()
    payload["seller_currency"] = "USD"

    response = client.post("/transactions", json=payload)

    body = response.json()
    assert response.status_code == 200
    assert body["negotiation_status"] == "ACCEPTED"
    assert body["policy_result"]["approved"] is False
    assert body["payment_status"] == "failed"


def test_health_endpoint_still_returns_200(client):
    response = client.get("/health")

    assert response.status_code == 200


def test_successful_transaction_response_structure_is_unchanged(client):
    response = client.post("/transactions", json=valid_payload())

    assert response.status_code == 200
    assert {
        "transaction",
        "negotiation_status",
        "policy_result",
        "payment_status",
        "message",
    } <= set(response.json())
