from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.webhooks.service import WebhookStatus, webhook_store


client = TestClient(app)


def setup_function():
    webhook_store.clear()


def test_create_webhook_returns_pending():
    payload = {
        "event": "transaction.completed",
        "transaction_id": "transaction-100",
        "status": "AUTHORIZED",
    }

    with patch(
        "backend.app.api.webhooks.deliver_webhook"
    ) as mock_delivery:
        response = client.post(
            "/webhooks",
            json={
                "url": "https://example.com/webhook",
                "payload": payload,
            },
            headers={
                "X-API-Key": "buyer-demo-key",
                "Idempotency-Key": "webhook-test-1",
            },
        )

    assert response.status_code == 202

    data = response.json()

    assert data["status"] == WebhookStatus.PENDING.value
    assert data["attempts"] == 0
    assert data["webhook_id"]

    mock_delivery.assert_called_once()


def test_webhook_requires_idempotency_key():
    response = client.post(
        "/webhooks",
        json={
            "url": "https://example.com/webhook",
            "payload": {"event": "test"},
        },
        headers={
            "X-API-Key": "buyer-demo-key",
        },
    )

    assert response.status_code == 400


def test_webhook_idempotency_is_scoped_to_api_key():
    payload = {
        "event": "transaction.completed",
    }

    with patch(
        "backend.app.api.webhooks.deliver_webhook"
    ):
        first = client.post(
            "/webhooks",
            json={
                "url": "https://example.com/webhook",
                "payload": payload,
            },
            headers={
                "X-API-Key": "buyer-demo-key",
                "Idempotency-Key": "same-key",
            },
        )

        second = client.post(
            "/webhooks",
            json={
                "url": "https://example.com/webhook",
                "payload": payload,
            },
            headers={
                "X-API-Key": "seller-demo-key",
                "Idempotency-Key": "same-key",
            },
        )

    assert first.status_code == 202
    assert second.status_code == 202

    assert first.json()["webhook_id"] != second.json()["webhook_id"]


def test_duplicate_webhook_is_blocked_while_processing():
    payload = {
        "event": "transaction.completed",
    }

    with patch(
        "backend.app.api.webhooks.deliver_webhook"
    ):
        first = client.post(
            "/webhooks",
            json={
                "url": "https://example.com/webhook",
                "payload": payload,
            },
            headers={
                "X-API-Key": "buyer-demo-key",
                "Idempotency-Key": "duplicate-key",
            },
        )

        second = client.post(
            "/webhooks",
            json={
                "url": "https://example.com/webhook",
                "payload": payload,
            },
            headers={
                "X-API-Key": "buyer-demo-key",
                "Idempotency-Key": "duplicate-key",
            },
        )

    assert first.status_code == 202
    assert second.status_code == 409