from enum import Enum
from typing import Optional

from pydantic import BaseModel

from backend.app.agents.seller import SellerAgent
from backend.app.models.transaction import Offer, PurchaseRequest


class NegotiationStatus(str, Enum):
    """The possible outcomes of a negotiation round."""

    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    COUNTER_OFFER = "COUNTER_OFFER"


class NegotiationResult(BaseModel):
    """The recorded outcome of a deterministic negotiation attempt."""

    status: NegotiationStatus
    rounds: int
    accepted_offer: Optional[Offer] = None
    reason: str
    history: list[str]


class NegotiationEngine:
    """Evaluates fixed seller offers against a buyer's purchase constraints."""

    def __init__(
        self,
        purchase_request: PurchaseRequest,
        seller_agent: SellerAgent,
        max_rounds: int = 3,
    ) -> None:
        if max_rounds < 1:
            raise ValueError("max_rounds must be at least 1")

        self._purchase_request = purchase_request
        self._seller_agent = seller_agent
        self._max_rounds = max_rounds
        self._rounds = 0
        self._history: list[str] = []

    def negotiate(self) -> NegotiationResult:
        """Evaluate the seller's fixed offer for the next negotiation round."""
        if self._rounds >= self._max_rounds:
            return NegotiationResult(
                status=NegotiationStatus.REJECTED,
                rounds=self._rounds,
                reason="Maximum negotiation rounds have already been exhausted.",
                history=self._history.copy(),
            )

        self._rounds += 1
        offer = self._seller_agent.create_offer(self._purchase_request)
        violations, total_cost = self._evaluate_offer(offer)

        if not violations:
            self._history.append(
                self._format_history_entry(offer, total_cost, passed=True)
            )
            return NegotiationResult(
                status=NegotiationStatus.ACCEPTED,
                rounds=self._rounds,
                accepted_offer=offer,
                reason="Offer satisfies all purchase constraints.",
                history=self._history.copy(),
            )

        self._history.append(
            self._format_history_entry(
                offer,
                total_cost,
                passed=False,
                violations=violations,
            )
        )

        if self._rounds >= self._max_rounds:
            return NegotiationResult(
                status=NegotiationStatus.REJECTED,
                rounds=self._rounds,
                reason="Maximum negotiation rounds exhausted: " + "; ".join(violations),
                history=self._history.copy(),
            )

        return NegotiationResult(
            status=NegotiationStatus.COUNTER_OFFER,
            rounds=self._rounds,
            reason="Offer requires a counter offer: " + "; ".join(violations),
            history=self._history.copy(),
        )

    def _evaluate_offer(self, offer: Offer) -> tuple[list[str], float]:
        """Return any offer violations and its calculated total cost."""
        total_cost = offer.quantity * offer.unit_price
        violations: list[str] = []

        if offer.quantity != self._purchase_request.quantity:
            violations.append(
                f"quantity {offer.quantity} does not match requested quantity "
                f"{self._purchase_request.quantity}"
            )
        if total_cost > self._purchase_request.max_budget:
            violations.append(
                f"total cost {total_cost} exceeds maximum budget "
                f"{self._purchase_request.max_budget}"
            )
        if offer.refund_days < self._purchase_request.minimum_refund_days:
            violations.append(
                f"refund days {offer.refund_days} is less than required minimum "
                f"{self._purchase_request.minimum_refund_days}"
            )

        return violations, total_cost

    def _format_history_entry(
        self,
        offer: Offer,
        total_cost: float,
        passed: bool,
        violations: Optional[list[str]] = None,
    ) -> str:
        """Format one complete, human-readable negotiation round record."""
        entry = (
            f"Round {self._rounds}: quantity={offer.quantity}, "
            f"unit_price={offer.unit_price}, total={total_cost}, "
            f"refund_days={offer.refund_days}; "
        )

        if passed:
            return entry + "PASSED."

        return entry + "FAILED: " + "; ".join(violations or [])
