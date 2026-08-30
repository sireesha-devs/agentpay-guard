from typing import Optional

from pydantic import BaseModel

from backend.app.agents.buyer import BuyerAgent
from backend.app.agents.seller import SellerAgent
from backend.app.audit.models import AuditRecord, ExecutionState
from backend.app.audit.recorder import AuditRecorder
from backend.app.models.transaction import (
    Offer,
    PolicyResult,
    PurchaseRequest,
    Transaction,
)
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
    """Coordinates existing agent, negotiation, policy, payment, and audit components."""

    def __init__(
        self,
        buyer_agent: BuyerAgent,
        seller_agent: SellerAgent,
        max_rounds: int = 3,
        audit_recorder: Optional[AuditRecorder] = None,
    ) -> None:
        self._buyer_agent = buyer_agent
        self._seller_agent = seller_agent
        self._max_rounds = max_rounds
        self._audit_recorder = audit_recorder

    def _record_audit(
        self,
        transaction_id: str,
        purchase_request: PurchaseRequest,
        execution_state: ExecutionState,
        payment_status: str,
        failure_message: Optional[str] = None,
    ) -> None:
        """Record an audit event when an audit recorder has been supplied."""
        if self._audit_recorder is None:
            return

        audit_record = AuditRecord(
            transaction_id=transaction_id,
            agent_id=purchase_request.buyer_id,
            model_version="deterministic-v1",
            prompt_hash="not-recorded",
            session_id=transaction_id,
            timestamp_utc=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
            requested_amount=purchase_request.max_budget,
            currency=purchase_request.currency,
            payment_method="not-specified",
            execution_state=execution_state,
            failure_message=failure_message,
        )

        self._audit_recorder.record(audit_record)

    def run(self, transaction_id: str) -> TransactionResult:
        """Run one deterministic purchase flow from request through payment."""

        purchase_request = self._buyer_agent.create_purchase_request()

        self._record_audit(
            transaction_id=transaction_id,
            purchase_request=purchase_request,
            execution_state=ExecutionState.PENDING,
            payment_status="pending",
        )

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

                self._record_audit(
                    transaction_id=transaction_id,
                    purchase_request=purchase_request,
                    execution_state=ExecutionState.BLOCKED,
                    payment_status="failed",
                    failure_message=(
                        "Transaction ended because negotiation was rejected."
                    ),
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

            self._record_audit(
                transaction_id=transaction_id,
                purchase_request=purchase_request,
                execution_state=ExecutionState.BLOCKED,
                payment_status="failed",
                failure_message=(
                    "Transaction ended because no accepted offer was available."
                ),
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

        policy_result = PolicyEngine().evaluate(
            purchase_request,
            accepted_offer,
        )

        transaction.policy_result = policy_result

        if not policy_result.approved:
            transaction.payment_status = "failed"

            self._record_audit(
                transaction_id=transaction_id,
                purchase_request=purchase_request,
                execution_state=ExecutionState.BLOCKED,
                payment_status="failed",
                failure_message=policy_result.reason,
            )

            return TransactionResult(
                transaction=transaction,
                negotiation_status=negotiation_status,
                policy_result=policy_result,
                payment_status="failed",
                message="Transaction was blocked by policy; payment was not attempted.",
            )

        self._record_audit(
            transaction_id=transaction_id,
            purchase_request=purchase_request,
            execution_state=ExecutionState.AUTHORIZED,
            payment_status="authorized",
        )

        payment_result = PaymentService().capture_payment(transaction)

        transaction.payment_status = payment_result.status.value

        if payment_result.status.value == "CAPTURED":
            execution_state = ExecutionState.CAPTURED
        else:
            execution_state = ExecutionState.FAILED

        self._record_audit(
            transaction_id=transaction_id,
            purchase_request=purchase_request,
            execution_state=execution_state,
            payment_status=payment_result.status.value,
            failure_message=(
                None
                if execution_state == ExecutionState.CAPTURED
                else payment_result.message
            ),
        )

        return TransactionResult(
            transaction=transaction,
            negotiation_status=negotiation_status,
            policy_result=policy_result,
            payment_status=payment_result.status.value,
            message=payment_result.message,
        )