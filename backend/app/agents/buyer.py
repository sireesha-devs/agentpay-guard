from backend.app.models.transaction import PurchaseRequest


class BuyerAgent:
    """Creates deterministic purchase requests from buyer-provided constraints."""

    def __init__(
        self,
        buyer_id: str,
        quantity: int,
        max_budget: float,
        currency: str,
        minimum_refund_days: int,
    ) -> None:
        self._buyer_id = buyer_id
        self._quantity = quantity
        self._max_budget = max_budget
        self._currency = currency
        self._minimum_refund_days = minimum_refund_days

    def create_purchase_request(self) -> PurchaseRequest:
        """Build and validate a purchase request using the stored constraints."""
        return PurchaseRequest(
            buyer_id=self._buyer_id,
            quantity=self._quantity,
            max_budget=self._max_budget,
            currency=self._currency,
            minimum_refund_days=self._minimum_refund_days,
        )
