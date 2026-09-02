from unittest.mock import patch

from backend.app.webhooks.service import (
    WebhookDelivery,
    WebhookStatus,
    generate_webhook_signature,
    validate_webhook_signature,
    webhook_store,
    deliver_webhook,
)


def setup_function():
    webhook_store.clear()


def test_webhook_signature_validation():
    payload = {
        "transaction_id": "transaction-1",
        "status": "AUTHORIZED",
    }

    secret = "test-secret"

    signature = generate_webhook_signature(payload, secret)

    assert validate_webhook_signature(
        payload,
        signature,
        secret,
    )

    assert not validate_webhook_signature(
        payload,
        "invalid-signature",
        secret,
    )


def test_webhook_delivered_on_first_attempt():
    payload = {
        "transaction_id": "transaction-1",
        "status": "AUTHORIZED",
    }

    signature = generate_webhook_signature(
        payload,
        "test-secret",
    )

    delivery = WebhookDelivery(
        webhook_id="webhook-1",
        url="https://example.com/webhook",
        payload=payload,
        signature=signature,
    )

    webhook_store.create(delivery)

    with patch(
        "backend.app.webhooks.service._send_webhook"
    ) as mock_send:
        result = deliver_webhook(
            "webhook-1",
            timeout=5.0,
            base_delay=0,
        )

    assert result.status == WebhookStatus.DELIVERED
    assert result.attempts == 1
    mock_send.assert_called_once()


def test_webhook_retries_then_succeeds():
    payload = {
        "transaction_id": "transaction-2",
        "status": "AUTHORIZED",
    }

    signature = generate_webhook_signature(
        payload,
        "test-secret",
    )

    delivery = WebhookDelivery(
        webhook_id="webhook-2",
        url="https://example.com/webhook",
        payload=payload,
        signature=signature,
    )

    webhook_store.create(delivery)

    with patch(
        "backend.app.webhooks.service._send_webhook"
    ) as mock_send:
        mock_send.side_effect = [
            RuntimeError("temporary failure"),
            RuntimeError("temporary failure"),
            None,
        ]

        result = deliver_webhook(
            "webhook-2",
            max_attempts=5,
            timeout=5.0,
            base_delay=0,
        )

    assert result.status == WebhookStatus.DELIVERED
    assert result.attempts == 3
    assert mock_send.call_count == 3


def test_webhook_becomes_exhausted_after_max_attempts():
    payload = {
        "transaction_id": "transaction-3",
        "status": "AUTHORIZED",
    }

    signature = generate_webhook_signature(
        payload,
        "test-secret",
    )

    delivery = WebhookDelivery(
        webhook_id="webhook-3",
        url="https://example.com/webhook",
        payload=payload,
        signature=signature,
    )

    webhook_store.create(delivery)

    with patch(
        "backend.app.webhooks.service._send_webhook"
    ) as mock_send:
        mock_send.side_effect = RuntimeError("permanent failure")

        result = deliver_webhook(
            "webhook-3",
            max_attempts=5,
            timeout=5.0,
            base_delay=0,
        )

    assert result.status == WebhookStatus.EXHAUSTED
    assert result.attempts == 5
    assert mock_send.call_count == 5
    assert result.last_error == "permanent failure"
def test_webhook_uses_explicit_http_timeout():
    payload = {
        "transaction_id": "transaction-timeout",
        "status": "AUTHORIZED",
    }

    signature = generate_webhook_signature(
        payload,
        "test-secret",
    )

    delivery = WebhookDelivery(
        webhook_id="webhook-timeout",
        url="https://example.com/webhook",
        payload=payload,
        signature=signature,
    )

    webhook_store.create(delivery)

    with patch(
        "backend.app.webhooks.service._send_webhook"
    ) as mock_send:
        mock_send.return_value = None

        deliver_webhook(
            "webhook-timeout",
            max_attempts=5,
            timeout=5.0,
            base_delay=0,
        )

    mock_send.assert_called_once_with(
        "https://example.com/webhook",
        payload,
        signature,
        5.0,
    )