from pydantic import BaseModel

from backend.app.agents.buyer import BuyerAgent
from backend.app.agents.seller import SellerAgent
from typing import Optional

from backend.app.models.transaction import Offer, PolicyResult, PurchaseRequest, Transaction
from backend.app.negotiation.engine import NegotiationEngine, NegotiationStatus
from backend.app.payments.service import PaymentService
from backend.app.policy.engine import PolicyEngine


class TransactionResult(BaseModel):
    """The final outcome of a complete deterministic transaction flow."""

    transaction: Transaction
    negotiation_status: str
    policy_result: PolicyResult
    payment_status: str
    message: str


class AgentPayOrchestrator:
    """Coordinates existing agent, negotiation, policy, and payment components."""

    def __init__(
        self,
        buyer_agent: BuyerAgent,
        seller_agent: SellerAgent,
        max_rounds: int = 3,
    ) -> None:
        self._buyer_agent = buyer_agent
        self._seller_agent = seller_agent
        self._max_rounds = max_rounds

    def run(self, transaction_id: str) -> TransactionResult:
        """Run one deterministic purchase flow from request through payment."""
        purchase_request = self._buyer_agent.create_purchase_request()
        negotiation_engine = NegotiationEngine(
            purchase_request,
            self._seller_agent,
            self._max_rounds,
        )

        while True:
            negotiation_result = negotiation_engine.negotiate()

            if negotiation_result.status == NegotiationStatus.ACCEPTED:
                return self._complete_accepted_negotiation(
                    transaction_id,
                    purchase_request,
                    negotiation_result.accepted_offer,
                    negotiation_result.status.value,
                )

            if negotiation_result.status == NegotiationStatus.REJECTED:
                policy_result = PolicyResult(
                    approved=False,
                    reason="Transaction blocked because no acceptable offer was negotiated.",
                    violations=["No acceptable offer was negotiated."],
                )
                transaction = Transaction(
                    transaction_id=transaction_id,
                    purchase_request=purchase_request,
                    policy_result=policy_result,
                    payment_status="failed",
                )
                return TransactionResult(
                    transaction=transaction,
                    negotiation_status=negotiation_result.status.value,
                    policy_result=policy_result,
                    payment_status="failed",
                    message="Transaction ended because negotiation was rejected; payment was not attempted.",
                )

    def _complete_accepted_negotiation(
        self,
        transaction_id: str,
        purchase_request: PurchaseRequest,
        accepted_offer: Optional[Offer],
        negotiation_status: str,
    ) -> TransactionResult:
        """Evaluate policy and capture payment for a successfully negotiated offer."""
        if accepted_offer is None:
            policy_result = PolicyResult(
                approved=False,
                reason="Transaction blocked because negotiation accepted no offer.",
                violations=["Negotiation accepted no offer."],
            )
            transaction = Transaction(
                transaction_id=transaction_id,
                purchase_request=purchase_request,
                policy_result=policy_result,
                payment_status="failed",
            )
            return TransactionResult(
                transaction=transaction,
                negotiation_status=negotiation_status,
                policy_result=policy_result,
                payment_status="failed",
                message="Transaction ended because no accepted offer was available for policy evaluation.",
            )

        transaction = Transaction(
            transaction_id=transaction_id,
            purchase_request=purchase_request,
            accepted_offer=accepted_offer,
            payment_status="pending",
        )
        policy_result = PolicyEngine().evaluate(purchase_request, accepted_offer)
        transaction.policy_result = policy_result

        if not policy_result.approved:
            transaction.payment_status = "failed"
            return TransactionResult(
                transaction=transaction,
                negotiation_status=negotiation_status,
                policy_result=policy_result,
                payment_status="failed",
                message="Transaction was blocked by policy; payment was not attempted.",
            )

        payment_result = PaymentService().capture_payment(transaction)
        transaction.payment_status = payment_result.status.value
        return TransactionResult(
            transaction=transaction,
            negotiation_status=negotiation_status,
            policy_result=policy_result,
            payment_status=payment_result.status.value,
            message=payment_result.message,
        )
