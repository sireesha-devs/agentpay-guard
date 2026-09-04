from __future__ import annotations

from dataclasses import dataclass

from backend.app.ai.providers.base import (
    AIProvider,
    AIProviderRequest,
    AIProviderResponse,
)


@dataclass(frozen=True)
class SafeFallback:
    """Conservative decision used when the AI provider fails."""

    decision: str = "BLOCK"
    risk_score: int = 100
    confidence: float = 1.0
    reasoning: str = (
        "AI evaluation was unavailable. Transaction blocked by safe fallback."
    )
    risk_factors: tuple[str, ...] = ("AI_PROVIDER_UNAVAILABLE",)
    recommended_action: str = "REJECT_TRANSACTION"


class SafeAIProvider(AIProvider):
    """
    AI provider wrapper with a fail-closed fallback.

    The wrapped provider is responsible for producing the AI decision.
    If it raises an exception, the transaction is conservatively blocked.
    """

    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    def evaluate(self, request: AIProviderRequest) -> AIProviderResponse:
        try:
            response = self._provider.evaluate(request)
        except Exception:
            fallback = SafeFallback()

            return AIProviderResponse(
                decision=fallback.decision,
                risk_score=fallback.risk_score,
                confidence=fallback.confidence,
                reasoning=fallback.reasoning,
                risk_factors=fallback.risk_factors,
                recommended_action=fallback.recommended_action,
            )

        return self._validate_response(response)

    @staticmethod
    def _validate_response(
        response: AIProviderResponse,
    ) -> AIProviderResponse:
        """Reject malformed provider output before it reaches the guardrail layer."""

        decision = response.decision.strip().upper()

        if decision not in {"APPROVE", "BLOCK", "REVIEW"}:
            return SafeAIProvider._fallback(
                "AI provider returned an invalid decision."
            )

        if not 0 <= response.risk_score <= 100:
            return SafeAIProvider._fallback(
                "AI provider returned an invalid risk score."
            )

        if not 0.0 <= response.confidence <= 1.0:
            return SafeAIProvider._fallback(
                "AI provider returned an invalid confidence score."
            )

        if not response.reasoning.strip():
            return SafeAIProvider._fallback(
                "AI provider returned empty reasoning."
            )

        return AIProviderResponse(
            decision=decision,
            risk_score=response.risk_score,
            confidence=response.confidence,
            reasoning=response.reasoning.strip(),
            risk_factors=tuple(response.risk_factors),
            recommended_action=response.recommended_action.strip(),
        )

    @staticmethod
    def _fallback(reason: str) -> AIProviderResponse:
        return AIProviderResponse(
            decision="BLOCK",
            risk_score=100,
            confidence=1.0,
            reasoning=reason,
            risk_factors=("AI_PROVIDER_INVALID_OUTPUT",),
            recommended_action="REJECT_TRANSACTION",
        )