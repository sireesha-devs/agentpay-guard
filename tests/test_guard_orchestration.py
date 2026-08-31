from datetime import datetime, timezone

from backend.app.agents.buyer import BuyerAgent
from backend.app.agents.seller import SellerAgent
from backend.app.audit.models import ExecutionState
from backend.app.audit.recorder import AuditRecorder
from backend.app.guards.budget import BudgetGuard
from backend.app.guards.pipeline import GuardPipeline
from backend.app.guards.risk import RiskGuardEvaluator
from backend.app.guards.velocity import VelocityGuard
from backend.app.orchestration.service import AgentPayOrchestrator


def create_orchestrator(
    recorder=None,
    budget_limit=1000.0,
    velocity_limit=5,
    restricted_categories=None,
):
    buyer = BuyerAgent(
        buyer_id="guard-agent-1",
        quantity=2,
        max_budget=1000.0,
        currency="INR",
        minimum_refund_days=7,
    )

    seller = SellerAgent(
        seller_id="guard-seller-1",
        unit_price=400.0,
        refund_days=7,
        currency="INR",
        terms="Seven-day return policy",
    )

    pipeline = GuardPipeline(
        budget_guard=BudgetGuard(budget_limit),
        velocity_guard=VelocityGuard(
            max_transactions=velocity_limit,
            window_seconds=60,
        ),
        risk_evaluator=RiskGuardEvaluator(
            allowed_merchants={"guard-seller-1"},
            restricted_categories=restricted_categories or {"restricted"},
        ),
    )

    return AgentPayOrchestrator(
        buyer,
        seller,
        max_rounds=3,
        audit_recorder=recorder,
        guard_pipeline=pipeline,
    )


def test_orchestrator_allows_transaction_when_guards_pass():
    orchestrator = create_orchestrator(
        budget_limit=5000.0,
    )

    result = orchestrator.run("guard-success-1")

    assert result.payment_status == "CAPTURED"


def test_budget_guard_blocks_before_payment():
    recorder = AuditRecorder()

    orchestrator = create_orchestrator(
        recorder=recorder,
        budget_limit=500.0,
    )

    result = orchestrator.run("guard-budget-block")

    assert result.payment_status == "failed"
    assert result.policy_result.approved is False

    events = recorder.get_events("guard-budget-block")

    assert events[-1].execution_state == ExecutionState.BLOCKED
    assert events[-1].failure_message is not None


def test_velocity_guard_blocks_before_payment():
    recorder = AuditRecorder()

    velocity_guard = VelocityGuard(
         max_transactions=1,
         window_seconds=60,
    )

    velocity_guard.record_execution(
         "velocity-agent",
         datetime.now(timezone.utc),
)

    buyer = BuyerAgent(
        buyer_id="velocity-agent",
        quantity=2,
        max_budget=1000.0,
        currency="INR",
        minimum_refund_days=7,
    )

    seller = SellerAgent(
        seller_id="velocity-seller",
        unit_price=400.0,
        refund_days=7,
        currency="INR",
        terms="Seven-day return policy",
    )

    pipeline = GuardPipeline(
        budget_guard=BudgetGuard(5000.0),
        velocity_guard=velocity_guard,
        risk_evaluator=RiskGuardEvaluator(
            allowed_merchants={"velocity-seller"},
            restricted_categories={"restricted"},
        ),
    )

    orchestrator = AgentPayOrchestrator(
        buyer,
        seller,
        max_rounds=3,
        audit_recorder=recorder,
        guard_pipeline=pipeline,
    )

    result = orchestrator.run("guard-velocity-block")

    assert result.payment_status == "failed"

    events = recorder.get_events("guard-velocity-block")

    assert events[-1].execution_state == ExecutionState.BLOCKED


def test_guard_pipeline_blocks_without_attempting_payment():
    recorder = AuditRecorder()

    orchestrator = create_orchestrator(
        recorder=recorder,
        budget_limit=500.0,
    )

    result = orchestrator.run("guard-no-payment")

    assert result.payment_status == "failed"

    events = recorder.get_events("guard-no-payment")

    states = [event.execution_state for event in events]

    assert ExecutionState.AUTHORIZED not in states
    assert ExecutionState.CAPTURED not in states


def test_audit_chain_remains_valid_after_guard_block():
    recorder = AuditRecorder()

    orchestrator = create_orchestrator(
        recorder=recorder,
        budget_limit=500.0,
    )

    orchestrator.run("guard-audit-chain")

    assert recorder.verify_chain() is True


def test_guard_block_contains_reason_in_result():
    orchestrator = create_orchestrator(
        budget_limit=500.0,
    )

    result = orchestrator.run("guard-reason")

    assert result.policy_result.approved is False
    assert "budget" in result.policy_result.reason.lower()