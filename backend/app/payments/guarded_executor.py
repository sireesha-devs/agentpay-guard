from __future__ import annotations

from dataclasses import dataclass

from backend.app.ai.decision import AIDecision
from backend.app.guards.guardrail import GuardrailEngine
from backend.app.guards.pipeline import GuardPipelineResult
from backend.app.payments.razorpay_gateway import (
    RazorpayGateway,
    RazorpayOrder,
)


@dataclass(frozen=True)
class GuardedPaymentResult:
    """Result of a guard-controlled Razorpay order attempt."""

    allowed: bool
    reason: str
    order: RazorpayOrder | None
    ai_decision: str
    deterministic_disposition: str


class GuardedRazorpayExecutor:
    """Executes Razorpay orders only after guardrail approval."""

    def __init__(
        self,
        gateway: RazorpayGateway,
        guardrail_engine: GuardrailEngine | None = None,
    ) -> None:
        self._gateway = gateway
        self._guardrail_engine = guardrail_engine or GuardrailEngine()

    def execute(
        self,
        ai_decision: AIDecision,
        guard_result: GuardPipelineResult,
        amount: float,
        currency: str,
        receipt: str,
    ) -> GuardedPaymentResult:
        """Create a Razorpay order only when all safety controls approve."""

        guardrail_decision = self._guardrail_engine.evaluate(
            ai_decision=ai_decision,
            guard_result=guard_result,
        )

        if not guardrail_decision.allowed:
            return GuardedPaymentResult(
                allowed=False,
                reason=guardrail_decision.reason,
                order=None,
                ai_decision=ai_decision.decision,
                deterministic_disposition=(
                    guard_result.final_disposition
                ),
            )

        order = self._gateway.create_order(
            amount=amount,
            currency=currency,
            receipt=receipt,
        )

        return GuardedPaymentResult(
            allowed=True,
            reason=guardrail_decision.reason,
            order=order,
            ai_decision=ai_decision.decision,
            deterministic_disposition=(
                guard_result.final_disposition
            ),
        )