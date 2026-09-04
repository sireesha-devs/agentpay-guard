from datetime import datetime, timezone

from backend.app.ai.decision import AIDecision
from backend.app.guards.guardrail import GuardrailEngine
from backend.app.guards.pipeline import (
    GuardCheckResult,
    GuardPipelineResult,
)


def make_ai_decision(decision: str) -> AIDecision:
    return AIDecision(
        decision=decision,
        risk_score=10 if decision == "APPROVE" else 90,
        confidence=0.99,
        reasoning="Test AI decision.",
        risk_factors=[],
        recommended_action=(
            "PROCEED_WITH_PAYMENT"
            if decision == "APPROVE"
            else "REJECT_TRANSACTION"
        ),
    )


def make_allowed_guard_result() -> GuardPipelineResult:
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


def make_blocked_guard_result() -> GuardPipelineResult:
    return GuardPipelineResult(
        allowed=False,
        final_disposition="BLOCKED",
        checks=(
            GuardCheckResult(
                guard_name="budget",
                passed=True,
                reason_code="BUDGET_OK",
                message="Budget check passed.",
            ),
            GuardCheckResult(
                guard_name="risk",
                passed=False,
                reason_code="RESTRICTED_CATEGORY",
                message="Restricted category.",
            ),
        ),
        timestamp_utc=datetime.now(timezone.utc),
    )


def test_approved_ai_and_allowed_guards_produce_approval():
    engine = GuardrailEngine()

    result = engine.evaluate(
        make_ai_decision("APPROVE"),
        make_allowed_guard_result(),
    )

    assert result.allowed is True
    assert result.decision == "APPROVE"
    assert result.blocked_by == ()


def test_deterministic_block_overrides_ai_approval():
    engine = GuardrailEngine()

    result = engine.evaluate(
        make_ai_decision("APPROVE"),
        make_blocked_guard_result(),
    )

    assert result.allowed is False
    assert result.decision == "BLOCK"
    assert result.blocked_by == ("RESTRICTED_CATEGORY",)
    assert "cannot override" in result.reason


def test_ai_rejection_blocks_transaction():
    engine = GuardrailEngine()

    result = engine.evaluate(
        make_ai_decision("BLOCK"),
        make_allowed_guard_result(),
    )

    assert result.allowed is False
    assert result.decision == "BLOCK"
    assert result.deterministic_disposition == "ALLOWED"