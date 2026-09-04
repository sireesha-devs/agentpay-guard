from backend.app.ai.providers.base import (
    AIProvider,
    AIProviderRequest,
    AIProviderResponse,
)
from backend.app.ai.service import AIDecisionService


class ApproveProvider(AIProvider):
    def evaluate(self, request: AIProviderRequest) -> AIProviderResponse:
        assert request.currency == "INR"
        assert request.merchant_id == "merchant-1"
        assert request.item_category == "electronics"

        return AIProviderResponse(
            decision="APPROVE",
            risk_score=15,
            confidence=0.94,
            reasoning="Transaction context appears normal.",
            risk_factors=("NORMAL_BEHAVIOR",),
            recommended_action="PROCEED_WITH_PAYMENT",
        )


class BlockProvider(AIProvider):
    def evaluate(self, request: AIProviderRequest) -> AIProviderResponse:
        return AIProviderResponse(
            decision="BLOCK",
            risk_score=95,
            confidence=0.98,
            reasoning="Transaction contains a high-risk pattern.",
            risk_factors=("HIGH_RISK_PATTERN",),
            recommended_action="REJECT_TRANSACTION",
        )


class FailingProvider(AIProvider):
    def evaluate(self, request: AIProviderRequest) -> AIProviderResponse:
        raise RuntimeError("provider unavailable")


def test_service_returns_structured_ai_decision():
    service = AIDecisionService(ApproveProvider())

    result = service.evaluate(
        transaction_id="tx-1",
        amount=500.0,
        currency=" inr ",
        merchant_id=" merchant-1 ",
        item_category=" Electronics ",
        context="Normal purchase",
    )

    assert result.decision == "APPROVE"
    assert result.risk_score == 15
    assert result.confidence == 0.94
    assert result.risk_factors == ["NORMAL_BEHAVIOR"]
    assert result.recommended_action == "PROCEED_WITH_PAYMENT"


def test_service_supports_block_decision():
    service = AIDecisionService(BlockProvider())

    result = service.evaluate(
        transaction_id="tx-2",
        amount=50000.0,
        currency="INR",
        merchant_id="merchant-2",
        item_category="electronics",
    )

    assert result.decision == "BLOCK"
    assert result.risk_score == 95
    assert "HIGH_RISK_PATTERN" in result.risk_factors


def test_service_fails_closed_when_provider_fails():
    service = AIDecisionService(FailingProvider())

    result = service.evaluate(
        transaction_id="tx-3",
        amount=1000.0,
        currency="INR",
        merchant_id="merchant-3",
        item_category="electronics",
    )

    assert result.decision == "BLOCK"
    assert result.risk_score == 100
    assert "AI_PROVIDER_UNAVAILABLE" in result.risk_factors
    assert result.recommended_action == "REJECT_TRANSACTION"