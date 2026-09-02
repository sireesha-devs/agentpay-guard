from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.idempotency.store import idempotency_store
from backend.app.webhooks.service import (
    WebhookStatus,
    webhook_store,
)


client = TestClient(app)


TRANSACTION_PAYLOAD = {
    "transaction_id": "concurrent-transaction",
    "buyer_id": "buyer-1",
    "quantity": 1,
    "max_budget": 100.0,
    "currency": "USD",
    "minimum_refund_days": 7,
    "seller_id": "seller-1",
    "unit_price": 50.0,
    "seller_currency": "USD",
    "refund_days": 7,
    "terms": "Standard terms",
    "max_rounds": 3,
}


def test_concurrent_transaction_requests_are_idempotent():
    """Only one concurrent request may process the same idempotency key."""

    idempotency_store.clear()

    barrier = Barrier(2)

    def send_request():
        barrier.wait()

        return client.post(
            "/transactions",
            headers={
                "X-API-Key": "buyer-demo-key",
                "Idempotency-Key": "concurrent-key",
            },
            json=TRANSACTION_PAYLOAD,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(send_request)
            for _ in range(2)
        ]

        responses = [future.result() for future in futures]

    status_codes = sorted(response.status_code for response in responses)

    assert status_codes == [200, 200]

    assert responses[0].json() == responses[1].json()

    record = idempotency_store.get(
        "transaction:buyer-demo-key:concurrent-key"
    )

    assert record is not None
    assert record.status == "COMPLETED"


def test_same_idempotency_key_is_scoped_by_api_key():
    """Different API keys may use the same idempotency key independently."""

    idempotency_store.clear()

    first = client.post(
        "/transactions",
        headers={
            "X-API-Key": "buyer-demo-key",
            "Idempotency-Key": "same-key",
        },
        json=TRANSACTION_PAYLOAD,
    )

    second = client.post(
        "/transactions",
        headers={
            "X-API-Key": "admin-demo-key",
            "Idempotency-Key": "same-key",
        },
        json=TRANSACTION_PAYLOAD,
    )

    assert first.status_code == 200
    assert second.status_code == 200

    buyer_record = idempotency_store.get(
        "transaction:buyer-demo-key:same-key"
    )
    admin_record = idempotency_store.get(
        "transaction:admin-demo-key:same-key"
    )

    assert buyer_record is not None
    assert admin_record is not None


def test_concurrent_webhook_creation_is_atomic():
    """Concurrent webhook requests with one key create only one delivery."""

    webhook_store.clear()

    barrier = Barrier(2)

    def create_webhook():
        barrier.wait()

        return client.post(
            "/webhooks",
            headers={
                "X-API-Key": "buyer-demo-key",
                "Idempotency-Key": "concurrent-webhook",
            },
            json={
                "url": "http://127.0.0.1:9999/webhook",
                "payload": {"event": "payment.completed"},
            },
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(create_webhook)
            for _ in range(2)
        ]

        responses = [future.result() for future in futures]

    status_codes = sorted(response.status_code for response in responses)

    assert status_codes in ([202, 409], [202, 202])

    records = [
        record
        for record in webhook_store._records.values()
        if record.webhook_id
        == "webhook:buyer-demo-key:concurrent-webhook"
    ]

    assert len(records) == 1