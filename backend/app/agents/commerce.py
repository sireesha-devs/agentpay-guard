from __future__ import annotations

from dataclasses import dataclass

from backend.app.agents.buyer import BuyerAgent
from backend.app.agents.seller import SellerAgent
from backend.app.models.transaction import Offer, PurchaseRequest


@dataclass(frozen=True)
class CommerceDecision:
    """Structured decision produced by the commerce agent."""

    approved: bool
    reason: str
    total_cost: float
    rounds_used: int
    purchase_request: PurchaseRequest
    offer: Offer


class CommerceAgent:
    """Orchestrates buyer and seller agents for agentic commerce.

    The commerce agent evaluates negotiated terms but has no payment authority.
    Deterministic guards remain the final enforcement layer.
    """

    def __init__(self, max_rounds: int = 3) -> None:
        if max_rounds < 1:
            raise ValueError("max_rounds must be at least 1")

        self.max_rounds = max_rounds

    def negotiate(
        self,
        buyer_agent: BuyerAgent,
        seller_agent: SellerAgent,
        rounds_used: int = 1,
    ) -> CommerceDecision:
        """Create a buyer request, obtain a seller offer, and evaluate it."""

        purchase_request = buyer_agent.create_purchase_request()
        offer = seller_agent.create_offer(purchase_request)

        return self.evaluate_offer(
            request=purchase_request,
            offer=offer,
            rounds_used=rounds_used,
        )

    def evaluate_offer(
        self,
        request: PurchaseRequest,
        offer: Offer,
        rounds_used: int = 1,
    ) -> CommerceDecision:
        """Evaluate whether an offer satisfies buyer constraints."""

        total_cost = offer.unit_price * offer.quantity

        if rounds_used < 1:
            raise ValueError("rounds_used must be at least 1")

        if rounds_used > self.max_rounds:
            return CommerceDecision(
                approved=False,
                reason="Maximum negotiation rounds exceeded.",
                total_cost=total_cost,
                rounds_used=self.max_rounds,
                purchase_request=request,
                offer=offer,
            )

        if offer.quantity != request.quantity:
            return CommerceDecision(
                approved=False,
                reason="Offered quantity does not match the requested quantity.",
                total_cost=total_cost,
                rounds_used=rounds_used,
                purchase_request=request,
                offer=offer,
            )

        if offer.currency.strip().upper() != request.currency.strip().upper():
            return CommerceDecision(
                approved=False,
                reason="Offer currency does not match the buyer currency.",
                total_cost=total_cost,
                rounds_used=rounds_used,
                purchase_request=request,
                offer=offer,
            )

        if offer.refund_days < request.minimum_refund_days:
            return CommerceDecision(
                approved=False,
                reason="Refund terms do not satisfy the buyer requirement.",
                total_cost=total_cost,
                rounds_used=rounds_used,
                purchase_request=request,
                offer=offer,
            )

        if total_cost > request.max_budget:
            return CommerceDecision(
                approved=False,
                reason="Offer exceeds the buyer's maximum budget.",
                total_cost=total_cost,
                rounds_used=rounds_used,
                purchase_request=request,
                offer=offer,
            )

        return CommerceDecision(
            approved=True,
            reason="Offer satisfies the buyer's purchase constraints.",
            total_cost=total_cost,
            rounds_used=rounds_used,
            purchase_request=request,
            offer=offer,
        )