from datetime import datetime, timezone
from unittest.mock import Mock

from backend.app.guards.pipeline import GuardPipeline


def make_payload():
    return Mock(amount=1000.0)


def test_budget_failure_short_circuits_downstream_guards():
    budget_guard = Mock()
    velocity_guard = Mock()
    risk_evaluator = Mock()

    budget_guard.can_spend.return_value = False

    pipeline = GuardPipeline(
        budget_guard=budget_guard,
        velocity_guard=velocity_guard,
        risk_evaluator=risk_evaluator,
    )

    result = pipeline.evaluate(
        payload=make_payload(),
        agent_id="agent-1",
        now=datetime.now(timezone.utc),
    )

    assert result.allowed is False
    assert result.final_disposition == "BLOCKED"

    assert len(result.checks) == 1
    assert result.checks[0].guard_name == "budget"
    assert result.checks[0].reason_code == "BUDGET_EXCEEDED"

    velocity_guard.can_execute.assert_not_called()
    risk_evaluator.evaluate.assert_not_called()


def test_velocity_failure_short_circuits_risk_guard():
    budget_guard = Mock()
    velocity_guard = Mock()
    risk_evaluator = Mock()

    budget_guard.can_spend.return_value = True
    velocity_guard.can_execute.return_value = False

    pipeline = GuardPipeline(
        budget_guard=budget_guard,
        velocity_guard=velocity_guard,
        risk_evaluator=risk_evaluator,
    )

    result = pipeline.evaluate(
        payload=make_payload(),
        agent_id="agent-1",
        now=datetime.now(timezone.utc),
    )

    assert result.allowed is False
    assert result.final_disposition == "BLOCKED"

    assert len(result.checks) == 2

    assert result.checks[0].guard_name == "budget"
    assert result.checks[0].passed is True

    assert result.checks[1].guard_name == "velocity"
    assert result.checks[1].passed is False
    assert result.checks[1].reason_code == "VELOCITY_LIMIT_EXCEEDED"

    risk_evaluator.evaluate.assert_not_called()
