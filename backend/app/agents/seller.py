from backend.app.models.transaction import Offer, PurchaseRequest


class SellerAgent:
    """Creates deterministic offers using fixed seller-provided terms."""

    def __init__(
        self,
        seller_id: str,
        unit_price: float,
        refund_days: int,
        currency: str,
        terms: str,
    ) -> None:
        self._seller_id = seller_id
        self._unit_price = unit_price
        self._refund_days = refund_days
        self._currency = currency
        self._terms = terms

    def create_offer(self, purchase_request: PurchaseRequest) -> Offer:
        """Create and validate an offer for the requested quantity."""
        return Offer(
            seller_id=self._seller_id,
            quantity=purchase_request.quantity,
            unit_price=self._unit_price,
            currency=self._currency,
            refund_days=self._refund_days,
            terms=self._terms,
        )
