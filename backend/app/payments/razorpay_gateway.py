from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import razorpay


@dataclass(frozen=True)
class RazorpayOrder:
    order_id: str
    amount: int
    currency: str
    status: str
    receipt: str


class RazorpayGateway:
    """Bounded Razorpay Test Mode gateway adapter."""

    def __init__(
        self,
        key_id: str | None = None,
        key_secret: str | None = None,
    ) -> None:
        self._key_id = key_id or os.getenv("RAZORPAY_KEY_ID")
        self._key_secret = key_secret or os.getenv("RAZORPAY_KEY_SECRET")

        if not self._key_id or not self._key_secret:
            raise ValueError(
                "Razorpay Test Mode credentials are required."
            )

        if not self._key_id.startswith("rzp_test_"):
            raise ValueError(
                "Only Razorpay Test Mode keys are allowed."
            )

        self._client = razorpay.Client(
            auth=(self._key_id, self._key_secret)
        )

    def create_order(
        self,
        amount: float,
        currency: str,
        receipt: str,
    ) -> RazorpayOrder:
        """Create a Razorpay Test Mode order."""

        if amount <= 0:
            raise ValueError("amount must be greater than zero")

        currency = currency.strip().upper()
        receipt = receipt.strip()

        if not currency:
            raise ValueError("currency is required")

        if not receipt:
            raise ValueError("receipt is required")

        amount_subunits = int(round(amount * 100))

        response: Any = self._client.order.create(
            data={
                "amount": amount_subunits,
                "currency": currency,
                "receipt": receipt,
            }
        )

        return RazorpayOrder(
            order_id=str(response["id"]),
            amount=int(response["amount"]),
            currency=str(response["currency"]),
            status=str(response["status"]),
            receipt=str(response["receipt"]),
        )