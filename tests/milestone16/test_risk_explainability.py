from datetime import datetime, timezone

from backend.app.ai.decision import AIDecision
from backend.app.ai.explainability import RiskExplainer
from backend.app.guards.pipeline import (
    GuardCheckResult,
    GuardPipelineResult,
)


def make_guard_result(allowed: bool) -> GuardPipelineResult:
    checks = (
        GuardCheckResult(
            guard_name="budget",
            passed=allowed,
            reason_code="BUDGET_OK" if allowed else "BUDGET_EXCEEDED",
            message="Budget check",
        ),
    )

    return GuardPipelineResult(
        allowed=allowed,
        final_disposition="ALLOWED" if allowed else "BLOCKED",
        checks=checks,
        timestamp_utc=datetime.now(timezone.utc),
    )


def test_explainer_describes_approved_transaction():
    ai_decision = AIDecision(
        decision="APPROVE",
        risk_score=10,
        confidence=0.99,
        reasoning="All deterministic guards passed.",
        risk_factors=[],
        recommended_action="PROCEED_WITH_PAYMENT",
    )

    explanation = RiskExplainer().explain(
        ai_decision,
        make_guard_result(True),
    )

    assert explanation.decision == "APPROVE"
    assert explanation.risk_score == 10
    assert explanation.confidence == 0.99
    assert "passed all deterministic guards" in explanation.summary
    assert explanation.risk_factors == ()
    assert "budget: PASSED (BUDGET_OK)" in explanation.guard_results
    assert explanation.recommended_action == "PROCEED_WITH_PAYMENT"


def test_explainer_prioritizes_deterministic_block():
    ai_decision = AIDecision(
        decision="APPROVE",
        risk_score=5,
        confidence=0.99,
        reasoning="Transaction appears safe.",
        risk_factors=[],
        recommended_action="PROCEED_WITH_PAYMENT",
    )

    explanation = RiskExplainer().explain(
        ai_decision,
        make_guard_result(False),
    )

    assert explanation.decision == "APPROVE"
    assert explanation.risk_score == 5
    assert "deterministic security guard failed" in explanation.summary
    assert "budget: FAILED (BUDGET_EXCEEDED)" in explanation.guard_results


def test_explainer_preserves_ai_risk_factors():
    ai_decision = AIDecision(
        decision="BLOCK",
        risk_score=95,
        confidence=0.99,
        reasoning="Restricted transaction category.",
        risk_factors=[
            "RESTRICTED_CATEGORY",
            "MERCHANT_NOT_ALLOWED",
        ],
        recommended_action="REJECT_TRANSACTION",
    )

    explanation = RiskExplainer().explain(
        ai_decision,
        make_guard_result(False),
    )

    assert explanation.decision == "BLOCK"
    assert explanation.risk_score == 95
    assert explanation.risk_factors == (
        "RESTRICTED_CATEGORY",
        "MERCHANT_NOT_ALLOWED",
    )
    assert explanation.recommended_action == "REJECT_TRANSACTION"


def test_explainer_handles_ai_rejection_after_guard_pass():
    ai_decision = AIDecision(
        decision="BLOCK",
        risk_score=60,
        confidence=0.85,
        reasoning="Elevated transaction risk.",
        risk_factors=["HIGH_VALUE_TRANSACTION"],
        recommended_action="REJECT_TRANSACTION",
    )

    explanation = RiskExplainer().explain(
        ai_decision,
        make_guard_result(True),
    )

    assert explanation.decision == "BLOCK"
    assert explanation.risk_score == 60
    assert explanation.confidence == 0.85
    assert "HIGH_VALUE_TRANSACTION" in explanation.risk_factors
    assert explanation.recommended_action == "REJECT_TRANSACTION"