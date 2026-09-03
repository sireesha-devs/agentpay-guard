from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.idempotency.store import idempotency_store
from backend.app.main import app
from backend.app.webhooks.service import (
    WebhookStatus,
    deliver_webhook,
    webhook_store,
)


client = TestClient(app)


def valid_payload(transaction_id: str = "m14-fault-1") -> dict[str, object]:
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


def test_transaction_succeeds_when_background_processing_fails():
    idempotency_store.clear()

    headers = {
        "X-API-Key": "buyer-demo-key",
        "Idempotency-Key": "m14-background-failure",
    }

    with patch(
    "backend.app.background._perform_transaction_post_processing",
    side_effect=RuntimeError("simulated background failure"),
    ):
        response = client.post(
            "/transactions",
            json=valid_payload("m14-background-failure"),
            headers=headers,
        )

    assert response.status_code == 200

    record = idempotency_store.get(
        "transaction:buyer-demo-key:m14-background-failure"
    )

    assert record is not None
    assert record.status == "COMPLETED"


def test_webhook_delivery_failure_is_retried_and_exhausted():
    webhook_store.clear()

    webhook_id = "m14-webhook-failure"

    from backend.app.webhooks.service import WebhookDelivery

    delivery = WebhookDelivery(
        webhook_id=webhook_id,
        url="https://example.com/webhook",
        payload={
            "event": "transaction.completed",
            "transaction_id": webhook_id,
            "status": "AUTHORIZED",
        },
        signature="test-signature",
    )

    webhook_store.create(delivery)

    with patch(
        "backend.app.webhooks.service._send_webhook",
        side_effect=RuntimeError("simulated network failure"),
    ):
        result = deliver_webhook(
            webhook_id,
            max_attempts=2,
            timeout=0.01,
            base_delay=0,
        )

    assert result.status == WebhookStatus.EXHAUSTED
    assert result.attempts == 2
    assert result.last_error == "simulated network failure"