from __future__ import annotations

from dataclasses import dataclass

from backend.app.ai.decision import AIDecision
from backend.app.ai.service import AIDecisionService
from backend.app.guards.guardrail import GuardrailDecision, GuardrailEngine
from backend.app.guards.pipeline import GuardPipelineResult


@dataclass(frozen=True)
class GuardedAIDecision:
    ai_decision: AIDecision
    guardrail_decision: GuardrailDecision
    final_decision: str
    allowed: bool
    reason: str


class GuardedAIDecisionService:
    """
    Combines AI recommendations with deterministic guardrails.

    Deterministic guardrails always have final authority.
    """

    def __init__(
        self,
        ai_service: AIDecisionService,
        guardrail_engine: GuardrailEngine | None = None,
    ) -> None:
        self._ai_service = ai_service
        self._guardrail_engine = guardrail_engine or GuardrailEngine()

    def evaluate(
        self,
        *,
        transaction_id: str,
        amount: float,
        currency: str,
        merchant_id: str,
        item_category: str,
        context: str,
        guard_result: GuardPipelineResult,
    ) -> GuardedAIDecision:
        ai_decision = self._ai_service.evaluate(
            transaction_id=transaction_id,
            amount=amount,
            currency=currency,
            merchant_id=merchant_id,
            item_category=item_category,
            context=context,
        )

        guardrail_decision = self._guardrail_engine.evaluate(
            ai_decision=ai_decision,
            guard_result=guard_result,
        )

        return GuardedAIDecision(
            ai_decision=ai_decision,
            guardrail_decision=guardrail_decision,
            final_decision=guardrail_decision.decision,
            allowed=guardrail_decision.allowed,
            reason=guardrail_decision.reason,
        )