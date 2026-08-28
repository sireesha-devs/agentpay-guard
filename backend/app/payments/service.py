from enum import Enum
from typing import Optional

from pydantic import BaseModel

from backend.app.models.transaction import Offer, Transaction


class PaymentStatus(str, Enum):
    """The lifecycle states represented by the deterministic payment service."""

    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"


class PaymentResult(BaseModel):
    """The deterministic outcome of a payment capture attempt."""

    transaction_id: str
    amount: float
    currency: str
    status: PaymentStatus
    message: str


class PaymentService:
    """Statelessly captures only transactions approved by the policy result."""

    def capture_payment(self, transaction: Transaction) -> PaymentResult:
        """Return a captured or failed payment result for the transaction."""
        offer = transaction.accepted_offer

        if transaction.policy_result is None:
            return self._failed_result(
                transaction,
                offer,
                "Payment failed: policy result is missing.",
            )
        if not transaction.policy_result.approved:
            return self._failed_result(
                transaction,
                offer,
                "Payment failed: transaction was rejected by policy.",
            )
        if offer is None:
            return self._failed_result(
                transaction,
                offer,
                "Payment failed: accepted offer is missing.",
            )

        amount = offer.quantity * offer.unit_price
        return PaymentResult(
            transaction_id=transaction.transaction_id,
            amount=amount,
            currency=offer.currency,
            status=PaymentStatus.CAPTURED,
            message="Payment captured for approved transaction.",
        )

    @staticmethod
    def _failed_result(
        transaction: Transaction,
        offer: Optional[Offer],
        message: str,
    ) -> PaymentResult:
        """Build a deterministic failure result without executing a payment."""
        amount = offer.quantity * offer.unit_price if offer is not None else 0.0
        currency = offer.currency if offer is not None else transaction.purchase_request.currency

        return PaymentResult(
            transaction_id=transaction.transaction_id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.FAILED,
            message=message,
        )
