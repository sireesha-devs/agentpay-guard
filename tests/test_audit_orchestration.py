from datetime import datetime, timezone

from backend.app.agents.buyer import BuyerAgent
from backend.app.agents.seller import SellerAgent
from backend.app.audit.models import ExecutionState
from backend.app.audit.recorder import AuditRecorder
from backend.app.orchestration.service import AgentPayOrchestrator


def create_successful_orchestrator(
    recorder: AuditRecorder,
) -> AgentPayOrchestrator:
    buyer = BuyerAgent(
        buyer_id="buyer-audit-1",
        quantity=2,
        max_budget=1000.0,
        currency="INR",
        minimum_refund_days=7,
    )

    seller = SellerAgent(
        seller_id="seller-audit-1",
        unit_price=400.0,
        refund_days=7,
        currency="INR",
        terms="Seven-day return policy",
    )

    return AgentPayOrchestrator(
        buyer,
        seller,
        max_rounds=3,
        audit_recorder=recorder,
    )


def test_successful_transaction_records_audit_lifecycle():
    recorder = AuditRecorder()
    orchestrator = create_successful_orchestrator(recorder)

    result = orchestrator.run("audit-transaction-1")

    events = recorder.get_events("audit-transaction-1")

    assert result.payment_status == "CAPTURED"
    assert [event.execution_state for event in events] == [
        ExecutionState.PENDING,
        ExecutionState.AUTHORIZED,
        ExecutionState.CAPTURED,
    ]


def test_audit_events_preserve_transaction_identity():
    recorder = AuditRecorder()
    orchestrator = create_successful_orchestrator(recorder)

    orchestrator.run("audit-transaction-2")

    events = recorder.get_events("audit-transaction-2")

    assert len(events) == 3

    for event in events:
        assert event.transaction_id == "audit-transaction-2"
        assert event.agent_id == "buyer-audit-1"
        assert event.currency == "INR"
        assert event.timestamp_utc.tzinfo is not None
        assert event.timestamp_utc.utcoffset() == timezone.utc.utcoffset(
            datetime.now(timezone.utc)
        )


def test_orchestrator_works_without_audit_recorder():
    buyer = BuyerAgent(
        buyer_id="buyer-no-audit",
        quantity=1,
        max_budget=500.0,
        currency="INR",
        minimum_refund_days=7,
    )

    seller = SellerAgent(
        seller_id="seller-no-audit",
        unit_price=400.0,
        refund_days=7,
        currency="INR",
        terms="Seven-day return policy",
    )

    orchestrator = AgentPayOrchestrator(
        buyer,
        seller,
        max_rounds=3,
    )

    result = orchestrator.run("no-audit-transaction")

    assert result.payment_status == "CAPTURED"


def test_policy_block_records_blocked_audit_event():
    recorder = AuditRecorder()

    buyer = BuyerAgent(
        buyer_id="buyer-blocked",
        quantity=2,
        max_budget=1000.0,
        currency="INR",
        minimum_refund_days=7,
    )

    seller = SellerAgent(
        seller_id="seller-blocked",
        unit_price=400.0,
        refund_days=5,
        currency="INR",
        terms="Five-day return policy",
    )

    orchestrator = AgentPayOrchestrator(
        buyer,
        seller,
        max_rounds=3,
        audit_recorder=recorder,
    )

    result = orchestrator.run("blocked-transaction")

    events = recorder.get_events("blocked-transaction")

    assert result.payment_status == "failed"
    assert events[-1].execution_state == ExecutionState.BLOCKED
    assert events[-1].failure_message is not None