from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.webhooks.service import webhook_store


client = TestClient(app)


def test_concurrent_webhook_creation_is_atomic():
    webhook_store.clear()

    payload = {
        "event": "transaction.completed",
        "transaction_id": "m14-concurrent-webhook",
        "status": "AUTHORIZED",
    }

    headers = {
        "X-API-Key": "buyer-demo-key",
        "Idempotency-Key": "m14-concurrent-webhook-key",
    }

    def send_request():
        return client.post(
            "/webhooks",
            json={
                "url": "https://example.com/webhook",
                "payload": payload,
            },
            headers=headers,
        )

    # Prevent real network delivery during the concurrency test.
    with patch(
        "backend.app.api.webhooks.deliver_webhook"
    ):
        with ThreadPoolExecutor(max_workers=10) as executor:
            responses = list(
                executor.map(
                    lambda _: send_request(),
                    range(10),
                )
            )

    accepted = [
        response
        for response in responses
        if response.status_code == 202
    ]

    conflicts = [
        response
        for response in responses
        if response.status_code == 409
    ]

    # Exactly one request should create the webhook.
    assert len(accepted) == 1

    # All remaining concurrent requests must be rejected
    # because the idempotency key is already being processed.
    assert len(conflicts) == 9

    # Only one webhook record must exist.
    assert len(webhook_store._records) == 1

    webhook_id = accepted[0].json()["webhook_id"]

    record = webhook_store.get(webhook_id)

    assert record is not None
    assert record.webhook_id == webhook_id