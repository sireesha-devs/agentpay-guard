from datetime import datetime, timezone

from backend.app.ai.decision import AIDecision
from backend.app.ai.guarded_decision import GuardedAIDecisionService
from backend.app.ai.providers.base import (
    AIProvider,
    AIProviderRequest,
    AIProviderResponse,
)
from backend.app.ai.service import AIDecisionService
from backend.app.guards.guardrail import GuardrailEngine
from backend.app.guards.pipeline import (
    GuardCheckResult,
    GuardPipelineResult,
)


class ApproveProvider(AIProvider):
    def evaluate(self, request: AIProviderRequest) -> AIProviderResponse:
        return AIProviderResponse(
            decision="APPROVE",
            risk_score=10,
            confidence=0.98,
            reasoning="Transaction appears legitimate.",
            risk_factors=(),
            recommended_action="PROCEED_WITH_PAYMENT",
        )


class BlockProvider(AIProvider):
    def evaluate(self, request: AIProviderRequest) -> AIProviderResponse:
        return AIProviderResponse(
            decision="BLOCK",
            risk_score=95,
            confidence=0.99,
            reasoning="Suspicious transaction pattern.",
            risk_factors=("SUSPICIOUS_PATTERN",),
            recommended_action="REJECT_TRANSACTION",
        )


def allowed_guard_result() -> GuardPipelineResult:
    return GuardPipelineResult(
        allowed=True,
        final_disposition="ALLOWED",
        checks=(
            GuardCheckResult(
                guard_name="budget",
                passed=True,
                reason_code="BUDGET_OK",
                message="Budget check passed.",
            ),
            GuardCheckResult(
                guard_name="velocity",
                passed=True,
                reason_code="VELOCITY_OK",
                message="Velocity check passed.",
            ),
            GuardCheckResult(
                guard_name="risk",
                passed=True,
                reason_code="RISK_CHECK_PASSED",
                message="Risk check passed.",
            ),
        ),
        timestamp_utc=datetime.now(timezone.utc),
    )


def blocked_guard_result() -> GuardPipelineResult:
    return GuardPipelineResult(
        allowed=False,
        final_disposition="BLOCKED",
        checks=(
            GuardCheckResult(
                guard_name="risk",
                passed=False,
                reason_code="MERCHANT_NOT_ALLOWED",
                message="Merchant is not allowed.",
            ),
        ),
        timestamp_utc=datetime.now(timezone.utc),
    )


def test_ai_approval_requires_deterministic_guardrail_approval():
    service = GuardedAIDecisionService(
        AIDecisionService(ApproveProvider()),
        GuardrailEngine(),
    )

    result = service.evaluate(
        transaction_id="tx-1",
        amount=500.0,
        currency="INR",
        merchant_id="merchant-1",
        item_category="electronics",
        context="Normal purchase",
        guard_result=allowed_guard_result(),
    )

    assert result.ai_decision.decision == "APPROVE"
    assert result.guardrail_decision.allowed is True
    assert result.final_decision == "APPROVE"
    assert result.allowed is True


def test_ai_block_prevents_payment_even_when_guards_pass():
    service = GuardedAIDecisionService(
        AIDecisionService(BlockProvider()),
        GuardrailEngine(),
    )

    result = service.evaluate(
        transaction_id="tx-2",
        amount=500.0,
        currency="INR",
        merchant_id="merchant-1",
        item_category="electronics",
        context="Suspicious purchase",
        guard_result=allowed_guard_result(),
    )

    assert result.ai_decision.decision == "BLOCK"
    assert result.guardrail_decision.allowed is False
    assert result.final_decision == "BLOCK"


def test_deterministic_guardrail_overrides_ai_approval():
    service = GuardedAIDecisionService(
        AIDecisionService(ApproveProvider()),
        GuardrailEngine(),
    )

    result = service.evaluate(
        transaction_id="tx-3",
        amount=500.0,
        currency="INR",
        merchant_id="merchant-1",
        item_category="electronics",
        context="Normal purchase",
        guard_result=blocked_guard_result(),
    )

    assert result.ai_decision.decision == "APPROVE"
    assert result.guardrail_decision.allowed is False
    assert result.final_decision == "BLOCK"
    assert result.allowed is False
    assert "deterministic" in result.reason.lower()