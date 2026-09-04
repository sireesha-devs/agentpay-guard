from __future__ import annotations

from backend.app.ai.decision import AIDecision
from backend.app.ai.providers.base import (
    AIProvider,
    AIProviderRequest,
)
from backend.app.ai.providers.safe import SafeAIProvider


class AIDecisionService:
    """
    Converts transaction context into an AI decision.

    This service only performs AI evaluation.
    It does not execute payments and cannot override
    deterministic guardrails.
    """

    def __init__(self, provider: AIProvider) -> None:
        self._provider = SafeAIProvider(provider)

    def evaluate(
        self,
        transaction_id: str,
        amount: float,
        currency: str,
        merchant_id: str,
        item_category: str,
        context: str = "",
    ) -> AIDecision:
        request = AIProviderRequest(
            transaction_id=transaction_id,
            amount=amount,
            currency=currency.strip().upper(),
            merchant_id=merchant_id.strip(),
            item_category=item_category.strip().lower(),
            context=context.strip(),
        )

        response = self._provider.evaluate(request)

        return AIDecision(
            decision=response.decision,
            risk_score=response.risk_score,
            confidence=response.confidence,
            reasoning=response.reasoning,
            risk_factors=list(response.risk_factors),
            recommended_action=response.recommended_action,
        )