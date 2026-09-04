import pytest

from backend.app.ai.providers.base import (
    AIProvider,
    AIProviderRequest,
    AIProviderResponse,
)
from backend.app.ai.providers.safe import SafeAIProvider


REQUEST = AIProviderRequest(
    transaction_id="tx-1",
    amount=100.0,
    currency="INR",
    merchant_id="merchant-1",
    item_category="electronics",
    context="Normal purchase",
)


class SuccessfulProvider(AIProvider):
    def evaluate(self, request: AIProviderRequest) -> AIProviderResponse:
        return AIProviderResponse(
            decision="APPROVE",
            risk_score=10,
            confidence=0.95,
            reasoning="Transaction appears legitimate.",
            risk_factors=(),
            recommended_action="PROCEED_WITH_PAYMENT",
        )


class FailingProvider(AIProvider):
    def evaluate(self, request: AIProviderRequest) -> AIProviderResponse:
        raise RuntimeError("AI service unavailable")


class InvalidDecisionProvider(AIProvider):
    def evaluate(self, request: AIProviderRequest) -> AIProviderResponse:
        return AIProviderResponse(
            decision="MAYBE",
            risk_score=10,
            confidence=0.95,
            reasoning="Unknown decision.",
            risk_factors=(),
            recommended_action="PROCEED",
        )


class InvalidRiskProvider(AIProvider):
    def evaluate(self, request: AIProviderRequest) -> AIProviderResponse:
        return AIProviderResponse(
            decision="APPROVE",
            risk_score=101,
            confidence=0.95,
            reasoning="Invalid risk.",
            risk_factors=(),
            recommended_action="PROCEED_WITH_PAYMENT",
        )


class EmptyReasoningProvider(AIProvider):
    def evaluate(self, request: AIProviderRequest) -> AIProviderResponse:
        return AIProviderResponse(
            decision="APPROVE",
            risk_score=10,
            confidence=0.95,
            reasoning="   ",
            risk_factors=(),
            recommended_action="PROCEED_WITH_PAYMENT",
        )


def test_successful_provider_result_passes_through():
    provider = SafeAIProvider(SuccessfulProvider())

    result = provider.evaluate(REQUEST)

    assert result.decision == "APPROVE"
    assert result.risk_score == 10
    assert result.confidence == 0.95
    assert result.recommended_action == "PROCEED_WITH_PAYMENT"


def test_provider_failure_fails_closed():
    provider = SafeAIProvider(FailingProvider())

    result = provider.evaluate(REQUEST)

    assert result.decision == "BLOCK"
    assert result.risk_score == 100
    assert result.confidence == 1.0
    assert result.recommended_action == "REJECT_TRANSACTION"
    assert "AI_PROVIDER_UNAVAILABLE" in result.risk_factors


def test_invalid_decision_fails_closed():
    provider = SafeAIProvider(InvalidDecisionProvider())

    result = provider.evaluate(REQUEST)

    assert result.decision == "BLOCK"
    assert result.risk_score == 100
    assert result.recommended_action == "REJECT_TRANSACTION"


def test_invalid_risk_score_fails_closed():
    provider = SafeAIProvider(InvalidRiskProvider())

    result = provider.evaluate(REQUEST)

    assert result.decision == "BLOCK"
    assert result.risk_score == 100


def test_empty_reasoning_fails_closed():
    provider = SafeAIProvider(EmptyReasoningProvider())

    result = provider.evaluate(REQUEST)

    assert result.decision == "BLOCK"
    assert result.risk_score == 100


def test_unexpected_provider_exception_is_not_exposed():
    provider = SafeAIProvider(FailingProvider())

    result = provider.evaluate(REQUEST)

    assert "AI service unavailable" not in result.reasoning
    assert "AI_PROVIDER_UNAVAILABLE" in result.risk_factors