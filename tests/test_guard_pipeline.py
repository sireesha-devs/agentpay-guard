from datetime import datetime, timezone

import pytest

from backend.app.guards.budget import BudgetGuard
from backend.app.guards.pipeline import GuardPipeline
from backend.app.guards.risk import (
    RiskGuardEvaluator,
    TransactionPayload,
)
from backend.app.guards.velocity import VelocityGuard


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def payload() -> TransactionPayload:
    return TransactionPayload(
        amount=5000.0,
        currency="INR",
        merchant_id="merchant-1",
        item_category="electronics",
    )


@pytest.fixture
def pipeline() -> GuardPipeline:
    return GuardPipeline(
        budget_guard=BudgetGuard(50000.0),
        velocity_guard=VelocityGuard(
            max_transactions=5,
            window_seconds=60,
        ),
        risk_evaluator=RiskGuardEvaluator(
            allowed_merchants={"merchant-1"},
            restricted_categories={"restricted"},
        ),
    )


def test_pipeline_allows_transaction_when_all_guards_pass(
    pipeline,
    payload,
    now,
):
    result = pipeline.evaluate(
        payload,
        agent_id="agent-1",
        now=now,
    )

    assert result.allowed is True
    assert result.final_disposition == "ALLOWED"
    assert len(result.checks) == 3
    assert all(check.passed for check in result.checks)


def test_pipeline_runs_guards_in_deterministic_order(
    pipeline,
    payload,
    now,
):
    result = pipeline.evaluate(
        payload,
        agent_id="agent-1",
        now=now,
    )

    assert [check.guard_name for check in result.checks] == [
        "budget",
        "velocity",
        "risk",
    ]


def test_budget_failure_short_circuits_pipeline(
    payload,
    now,
):
    pipeline = GuardPipeline(
        budget_guard=BudgetGuard(1000.0),
        velocity_guard=VelocityGuard(
            max_transactions=5,
            window_seconds=60,
        ),
        risk_evaluator=RiskGuardEvaluator(
            allowed_merchants={"merchant-1"},
            restricted_categories={"restricted"},
        ),
    )

    result = pipeline.evaluate(
        payload,
        agent_id="agent-1",
        now=now,
    )

    assert result.allowed is False
    assert result.final_disposition == "BLOCKED"
    assert len(result.checks) == 1
    assert result.checks[0].guard_name == "budget"
    assert result.checks[0].reason_code == "BUDGET_EXCEEDED"


def test_velocity_failure_short_circuits_before_risk(
    payload,
    now,
):
    velocity_guard = VelocityGuard(
        max_transactions=1,
        window_seconds=60,
    )

    velocity_guard.record_execution(
        "agent-1",
        now,
    )

    pipeline = GuardPipeline(
        budget_guard=BudgetGuard(50000.0),
        velocity_guard=velocity_guard,
        risk_evaluator=RiskGuardEvaluator(
            allowed_merchants={"merchant-1"},
            restricted_categories={"restricted"},
        ),
    )

    result = pipeline.evaluate(
        payload,
        agent_id="agent-1",
        now=now,
    )

    assert result.allowed is False
    assert result.final_disposition == "BLOCKED"
    assert len(result.checks) == 2
    assert result.checks[0].guard_name == "budget"
    assert result.checks[1].guard_name == "velocity"
    assert result.checks[1].reason_code == "VELOCITY_LIMIT_EXCEEDED"


def test_risk_failure_blocks_after_budget_and_velocity(
    payload,
    now,
):
    risky_payload = payload.model_copy(
        update={"item_category": "restricted"}
    )

    pipeline = GuardPipeline(
        budget_guard=BudgetGuard(50000.0),
        velocity_guard=VelocityGuard(
            max_transactions=5,
            window_seconds=60,
        ),
        risk_evaluator=RiskGuardEvaluator(
            allowed_merchants={"merchant-1"},
            restricted_categories={"restricted"},
        ),
    )

    result = pipeline.evaluate(
        risky_payload,
        agent_id="agent-1",
        now=now,
    )

    assert result.allowed is False
    assert result.final_disposition == "BLOCKED"
    assert len(result.checks) == 3
    assert result.checks[-1].guard_name == "risk"
    assert result.checks[-1].passed is False


def test_pipeline_result_is_immutable(
    pipeline,
    payload,
    now,
):
    result = pipeline.evaluate(
        payload,
        agent_id="agent-1",
        now=now,
    )

    with pytest.raises(AttributeError):
        result.allowed = False


def test_pipeline_preserves_timestamp(
    pipeline,
    payload,
    now,
):
    result = pipeline.evaluate(
        payload,
        agent_id="agent-1",
        now=now,
    )

    assert result.timestamp_utc == now


def test_naive_datetime_is_rejected(
    pipeline,
    payload,
):
    naive_now = datetime(2026, 8, 31, 12, 0)

    with pytest.raises(ValueError):
        pipeline.evaluate(
            payload,
            agent_id="agent-1",
            now=naive_now,
        )