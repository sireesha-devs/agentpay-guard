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
        "transaction_id": "api-transaction-1",
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


def test_successful_transaction_returns_captured(client):
    response = client.post(
        "/transactions",
        json=valid_payload(),
        headers={"Idempotency-Key": "test-successful-transaction"},
    )

    assert response.status_code == 200
    assert response.json()["payment_status"] == "CAPTURED"


def test_transaction_id_is_returned(client):
    response = client.post(
        "/transactions",
        json=valid_payload(),
        headers={"Idempotency-Key": "test-transaction-id"},
    )

    assert response.json()["transaction"]["transaction_id"] == "api-transaction-1"


def test_successful_transaction_returns_accepted_offer(client):
    response = client.post(
        "/transactions",
        json=valid_payload(),
        headers={"Idempotency-Key": "test-accepted-offer"},
    )

    assert response.json()["transaction"]["accepted_offer"]["seller_id"] == "seller-1"


def test_successful_transaction_returns_approved_policy_result(client):
    response = client.post(
        "/transactions",
        json=valid_payload(),
        headers={"Idempotency-Key": "test-approved-policy"},
    )

    assert response.json()["policy_result"]["approved"] is True


def test_over_budget_seller_returns_rejected_transaction(client):
    payload = valid_payload()
    payload["unit_price"] = 600.0

    response = client.post(
        "/transactions",
        json=payload,
        headers={"Idempotency-Key": "test-over-budget"},
    )

    assert response.status_code == 200
    assert response.json()["negotiation_status"] == "REJECTED"
    assert response.json()["payment_status"] == "failed"


def test_currency_mismatch_blocks_payment_at_policy(client):
    payload = valid_payload()
    payload["seller_currency"] = "USD"

    response = client.post(
        "/transactions",
        json=payload,
        headers={"Idempotency-Key": "test-currency-mismatch"},
    )

    body = response.json()
    assert body["negotiation_status"] == "ACCEPTED"
    assert body["policy_result"]["approved"] is False
    assert body["payment_status"] == "failed"


def test_insufficient_refund_days_returns_rejected_transaction(client):
    payload = valid_payload()
    payload["refund_days"] = 5

    response = client.post(
        "/transactions",
        json=payload,
        headers={"Idempotency-Key": "test-refund-days"},
    )

    assert response.status_code == 200
    assert response.json()["negotiation_status"] == "REJECTED"


def test_invalid_request_data_returns_422(client):
    payload = valid_payload()
    payload["quantity"] = 0

    response = client.post(
        "/transactions",
        json=payload,
        headers={"Idempotency-Key": "test-invalid-request"},
    )

    assert response.status_code == 422


def test_health_endpoint_still_returns_200(client):
    response = client.get("/health")

    assert response.status_code == 200


def test_transaction_response_contains_expected_fields(client):
    response = client.post(
        "/transactions",
        json=valid_payload(),
        headers={"Idempotency-Key": "test-response-fields"},
    )

    body = response.json()
    assert {"transaction", "negotiation_status", "policy_result", "payment_status", "message"} <= set(body)