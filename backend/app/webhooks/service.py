from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any


logger = logging.getLogger("agentpay.guard.webhooks")


class WebhookStatus(str, Enum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    EXHAUSTED = "EXHAUSTED"


@dataclass
class WebhookDelivery:
    webhook_id: str
    url: str
    payload: dict[str, Any]
    signature: str
    status: WebhookStatus = WebhookStatus.PENDING
    attempts: int = 0
    last_error: str | None = None
    delivery_lock: Lock = field(
        default_factory=Lock,
        repr=False,
        compare=False,
    )


class WebhookDeliveryStore:
    """Thread-safe process-local webhook delivery store."""

    def __init__(self) -> None:
        self._records: dict[str, WebhookDelivery] = {}
        self._lock = Lock()

    def create(self, delivery: WebhookDelivery) -> None:
        with self._lock:
            if delivery.webhook_id in self._records:
                raise ValueError(
                    f"Webhook already exists: {delivery.webhook_id}"
                )

            self._records[delivery.webhook_id] = delivery

    def create_if_absent(self, delivery: WebhookDelivery) -> bool:
        """Atomically create a webhook only if its ID does not exist."""
        with self._lock:
            if delivery.webhook_id in self._records:
                return False

            self._records[delivery.webhook_id] = delivery
            return True

    def get(self, webhook_id: str) -> WebhookDelivery | None:
        with self._lock:
            return self._records.get(webhook_id)

    def update(
        self,
        webhook_id: str,
        *,
        status: WebhookStatus | None = None,
        attempts: int | None = None,
        last_error: str | None = None,
    ) -> None:
        with self._lock:
            record = self._records.get(webhook_id)

            if record is None:
                raise KeyError(f"Unknown webhook: {webhook_id}")

            if status is not None:
                record.status = status

            if attempts is not None:
                record.attempts = attempts

            if last_error is not None:
                record.last_error = last_error

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


webhook_store = WebhookDeliveryStore()


def generate_webhook_signature(
    payload: dict[str, Any],
    secret: str,
) -> str:
    """Generate an HMAC-SHA256 signature for a webhook payload."""

    body = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()


def validate_webhook_signature(
    payload: dict[str, Any],
    signature: str,
    secret: str,
) -> bool:
    """Validate a webhook HMAC-SHA256 signature."""

    expected = generate_webhook_signature(payload, secret)

    return hmac.compare_digest(expected, signature)


def _send_webhook(
    url: str,
    payload: dict[str, Any],
    signature: str,
    timeout: float,
) -> None:
    """Send one webhook request."""

    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme not in {"http", "https"}:
        raise ValueError("Webhook URL must use http or https")
    if not parsed_url.netloc:
        raise ValueError("Webhook URL must include a host")

    body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
        },
    )

    with urllib.request.urlopen(  # nosec B310
    request,
    timeout=timeout,
    ) as response:
        status_code = response.status

        if not 200 <= status_code < 300:
            raise RuntimeError(
                f"Webhook returned HTTP {status_code}"
            )


def deliver_webhook(
    webhook_id: str,
    *,
    max_attempts: int = 5,
    timeout: float = 5.0,
    base_delay: float = 1.0,
) -> WebhookDelivery:
    """
    Deliver a webhook with exponential-backoff retries.

    Concurrent delivery calls for the same webhook are serialized.
    """

    delivery = webhook_store.get(webhook_id)

    if delivery is None:
        raise KeyError(f"Unknown webhook: {webhook_id}")

    with delivery.delivery_lock:
        if delivery.status == WebhookStatus.DELIVERED:
            return delivery

        if delivery.status == WebhookStatus.EXHAUSTED:
            return delivery

        for attempt in range(1, max_attempts + 1):
            webhook_store.update(
                webhook_id,
                status=WebhookStatus.PENDING,
                attempts=attempt,
            )

            try:
                _send_webhook(
                    delivery.url,
                    delivery.payload,
                    delivery.signature,
                    timeout,
                )

                webhook_store.update(
                    webhook_id,
                    status=WebhookStatus.DELIVERED,
                )

                logger.info(
                    "Webhook delivered",
                    extra={
                        "event": "webhook_delivered",
                        "webhook_id": webhook_id,
                        "attempt": attempt,
                    },
                )

                return delivery

            except Exception as exc:
                error = str(exc)

                webhook_store.update(
                    webhook_id,
                    status=WebhookStatus.FAILED,
                    attempts=attempt,
                    last_error=error,
                )

                logger.warning(
                    "Webhook delivery failed",
                    extra={
                        "event": "webhook_delivery_failed",
                        "webhook_id": webhook_id,
                        "attempt": attempt,
                        "error": error,
                    },
                )

                if attempt >= max_attempts:
                    webhook_store.update(
                        webhook_id,
                        status=WebhookStatus.EXHAUSTED,
                    )
                    return delivery

                time.sleep(base_delay * (2 ** (attempt - 1)))

    return delivery
