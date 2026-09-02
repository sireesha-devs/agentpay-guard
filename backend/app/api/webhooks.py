from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from backend.app.security.auth import authenticate
from backend.app.webhooks.service import (
    WebhookDelivery,
    WebhookStatus,
    deliver_webhook,
    generate_webhook_signature,
    webhook_store,
)


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookCreateRequest(BaseModel):
    """Request model for creating a webhook delivery."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    url: str = Field(min_length=1, max_length=2048)
    payload: dict[str, Any]


class WebhookCreateResponse(BaseModel):
    """Response returned when a webhook is created."""

    webhook_id: str
    status: WebhookStatus
    attempts: int


def _webhook_secret() -> str:
    return os.getenv(
        "AGENTPAY_WEBHOOK_SECRET",
        "agentpay-development-secret",
    )


@router.post(
    "",
    response_model=WebhookCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a webhook delivery",
    responses={
        400: {"description": "Missing Idempotency-Key."},
        401: {"description": "Missing or invalid API key."},
        409: {"description": "Webhook idempotency key already processed."},
        422: {"description": "Request validation failed."},
        429: {"description": "Rate limit exceeded."},
    },
)
def create_webhook(
    request: WebhookCreateRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(
        default=None,
        alias="X-API-Key",
    ),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
    ),
) -> WebhookCreateResponse:
    """Create and asynchronously deliver a signed webhook."""

    authenticate(x_api_key)

    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key header is required",
        )

    scoped_key = (
        f"webhook:{x_api_key}:{idempotency_key.strip()}"
    )

    webhook_id = scoped_key

    signature = generate_webhook_signature(
        request.payload,
        _webhook_secret(),
    )

    delivery = WebhookDelivery(
        webhook_id=webhook_id,
        url=request.url,
        payload=request.payload,
        signature=signature,
    )

    created = webhook_store.create_if_absent(delivery)

    if not created:
        existing = webhook_store.get(scoped_key)

        if existing is not None and existing.status == WebhookStatus.DELIVERED:
            return WebhookCreateResponse(
                webhook_id=existing.webhook_id,
                status=existing.status,
                attempts=existing.attempts,
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Webhook with this idempotency key is already processing",
        )

    background_tasks.add_task(
        deliver_webhook,
        webhook_id,
    )

    return WebhookCreateResponse(
        webhook_id=webhook_id,
        status=WebhookStatus.PENDING,
        attempts=0,
    )