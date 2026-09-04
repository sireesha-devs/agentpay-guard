from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RazorpayConfig:
    """Razorpay Test Mode configuration."""

    key_id: str
    key_secret: str

    @classmethod
    def from_environment(cls) -> RazorpayConfig:
        key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
        key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()

        if not key_id or not key_secret:
            raise ValueError(
                "Razorpay Test Mode credentials are required."
            )

        if not key_id.startswith("rzp_test_"):
            raise ValueError(
                "Only Razorpay Test Mode keys are allowed."
            )

        return cls(
            key_id=key_id,
            key_secret=key_secret,
        )