from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.idempotency.store import idempotency_store
from backend.app.main import app


client = TestClient(app)


def valid_payload(transaction_id: str = "m14-replay-1"):
    return {
        "transaction_id": transaction_id,
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


def test_same_idempotency_key_isolated_across_api_keys():
    idempotency_store.clear()

    key = "m14-collision-key"

    with patch(
        "backend.app.api.transactions.process_transaction_post_processing"
    ):
        buyer_response = client.post(
            "/transactions",
            json=valid_payload("buyer-transaction"),
            headers={
                "X-API-Key": "buyer-demo-key",
                "Idempotency-Key": key,
            },
        )

        admin_response = client.post(
            "/transactions",
            json=valid_payload("admin-transaction"),
            headers={
                "X-API-Key": "admin-demo-key",
                "Idempotency-Key": key,
            },
        )

    assert buyer_response.status_code == 200
    assert admin_response.status_code == 200

    # The same idempotency key must not leak the first
    # tenant's transaction result into the second tenant.
    assert buyer_response.json() != admin_response.json()

    assert (
        idempotency_store.get(
            f"transaction:buyer-demo-key:{key}"
        )
        is not None
    )

    assert (
        idempotency_store.get(
            f"transaction:admin-demo-key:{key}"
        )
        is not None
    )


def test_replay_with_same_key_returns_original_result():
    idempotency_store.clear()

    key = "m14-replay-key"

    with patch(
        "backend.app.api.transactions.process_transaction_post_processing"
    ):
        first_response = client.post(
            "/transactions",
            json=valid_payload("original-transaction"),
            headers={
                "X-API-Key": "buyer-demo-key",
                "Idempotency-Key": key,
            },
        )

        replay_payload = valid_payload("modified-transaction")
        replay_payload["unit_price"] = 999.0

        replay_response = client.post(
            "/transactions",
            json=replay_payload,
            headers={
                "X-API-Key": "buyer-demo-key",
                "Idempotency-Key": key,
            },
        )

    assert first_response.status_code == 200
    assert replay_response.status_code == 200

    # The completed idempotency key returns the cached original result.
    assert replay_response.json() == first_response.json()