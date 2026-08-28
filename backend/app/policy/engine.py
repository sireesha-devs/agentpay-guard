from backend.app.models.transaction import Offer, PolicyResult, PurchaseRequest


class PolicyEngine:
    """Deterministically validates an offer against a purchase request."""

    def evaluate(
        self,
        purchase_request: PurchaseRequest,
        offer: Offer,
    ) -> PolicyResult:
        """Return approval only when the offer satisfies every policy rule."""
        total_cost = offer.quantity * offer.unit_price
        violations: list[str] = []

        if offer.quantity != purchase_request.quantity:
            violations.append(
                f"Offer quantity {offer.quantity} does not match requested quantity "
                f"{purchase_request.quantity}."
            )
        if total_cost > purchase_request.max_budget:
            violations.append(
                f"Offer total cost {total_cost} exceeds maximum budget "
                f"{purchase_request.max_budget}."
            )
        if offer.refund_days < purchase_request.minimum_refund_days:
            violations.append(
                f"Offer refund days {offer.refund_days} is less than minimum refund "
                f"days {purchase_request.minimum_refund_days}."
            )
        if offer.currency != purchase_request.currency:
            violations.append(
                f"Offer currency {offer.currency} does not match requested currency "
                f"{purchase_request.currency}."
            )

        if violations:
            return PolicyResult(
                approved=False,
                reason="Transaction blocked because the offer failed one or more policy checks.",
                violations=violations,
            )

        return PolicyResult(
            approved=True,
            reason="Offer passed all policy checks.",
            violations=[],
        )
