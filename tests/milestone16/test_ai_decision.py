from datetime import datetime, timezone

from backend.app.ai.decision import AIDecisionEngine
from backend.app.guards.pipeline import GuardCheckResult, GuardPipelineResult


def test_ai_decision_approves_when_all_guards_pass():
    result = GuardPipelineResult(
        allowed=True,
        final_disposition="ALLOWED",
        checks=(
            GuardCheckResult(
                guard_name="budget",
                passed=True,
                reason_code="BUDGET_OK",
                message="Transaction is within the remaining budget.",
            ),
            GuardCheckResult(
                guard_name="velocity",
                passed=True,
                reason_code="VELOCITY_OK",
                message="Transaction velocity is within the configured limit.",
            ),
            GuardCheckResult(
                guard_name="risk",
                passed=True,
                reason_code="RISK_CHECK_PASSED",
                message="Risk checks passed.",
            ),
        ),
        timestamp_utc=datetime.now(timezone.utc),
    )

    decision = AIDecisionEngine().evaluate(result)

    assert decision.decision == "APPROVE"
    assert decision.risk_score == 10
    assert decision.confidence == 0.99
    assert decision.risk_factors == []
    assert decision.recommended_action == "PROCEED_WITH_PAYMENT"


def test_ai_decision_blocks_on_budget_failure():
    result = GuardPipelineResult(
        allowed=False,
        final_disposition="BLOCKED",
        checks=(
            GuardCheckResult(
                guard_name="budget",
                passed=False,
                reason_code="BUDGET_EXCEEDED",
                message="Transaction exceeds the remaining budget.",
            ),
        ),
        timestamp_utc=datetime.now(timezone.utc),
    )

    decision = AIDecisionEngine().evaluate(result)

    assert decision.decision == "BLOCK"
    assert decision.risk_score == 90
    assert "BUDGET_EXCEEDED" in decision.risk_factors
    assert decision.recommended_action == "REJECT_TRANSACTION"
    assert "cannot override" in decision.reasoning


def test_ai_decision_blocks_on_risk_failure():
    result = GuardPipelineResult(
        allowed=False,
        final_disposition="BLOCKED",
        checks=(
            GuardCheckResult(
                guard_name="budget",
                passed=True,
                reason_code="BUDGET_OK",
                message="Transaction is within the remaining budget.",
            ),
            GuardCheckResult(
                guard_name="velocity",
                passed=True,
                reason_code="VELOCITY_OK",
                message="Transaction velocity is within the configured limit.",
            ),
            GuardCheckResult(
                guard_name="risk",
                passed=False,
                reason_code="MERCHANT_NOT_ALLOWED",
                message="Merchant is not on the allowed merchant list.",
            ),
        ),
        timestamp_utc=datetime.now(timezone.utc),
    )

    decision = AIDecisionEngine().evaluate(result)

    assert decision.decision == "BLOCK"
    assert decision.risk_score == 95
    assert decision.risk_factors == ["MERCHANT_NOT_ALLOWED"]
    assert decision.recommended_action == "REJECT_TRANSACTION"


def test_ai_decision_output_is_bounded():
    result = GuardPipelineResult(
        allowed=True,
        final_disposition="ALLOWED",
        checks=(),
        timestamp_utc=datetime.now(timezone.utc),
    )

    decision = AIDecisionEngine().evaluate(result)

    assert 0 <= decision.risk_score <= 100
    assert 0.0 <= decision.confidence <= 1.0
