from backend.app.ai.providers.base import (
    AIProvider,
    AIProviderRequest,
    AIProviderResponse,
)


class FakeAIProvider(AIProvider):
    def evaluate(self, request: AIProviderRequest) -> AIProviderResponse:
        return AIProviderResponse(
            decision="APPROVE",
            risk_score=10,
            confidence=0.95,
            reasoning="Transaction context is consistent.",
            risk_factors=(),
            recommended_action="PROCEED_WITH_PAYMENT",
        )


def test_provider_request_contains_transaction_context():
    request = AIProviderRequest(
        transaction_id="tx-1",
        amount=100.0,
        currency="INR",
        merchant_id="merchant-1",
        item_category="electronics",
        context="Normal purchase",
    )

    assert request.transaction_id == "tx-1"
    assert request.amount == 100.0
    assert request.currency == "INR"


def test_provider_response_is_structured():
    response = AIProviderResponse(
        decision="BLOCK",
        risk_score=90,
        confidence=0.98,
        reasoning="High-risk transaction.",
        risk_factors=("HIGH_AMOUNT",),
        recommended_action="REJECT_TRANSACTION",
    )

    assert response.decision == "BLOCK"
    assert response.risk_score == 90
    assert response.risk_factors == ("HIGH_AMOUNT",)


def test_fake_provider_implements_contract():
    provider = FakeAIProvider()

    result = provider.evaluate(
        AIProviderRequest(
            transaction_id="tx-1",
            amount=100.0,
            currency="INR",
            merchant_id="merchant-1",
            item_category="electronics",
            context="Normal purchase",
        )
    )

    assert result.decision == "APPROVE"
    assert result.recommended_action == "PROCEED_WITH_PAYMENT"