from datetime import datetime, timezone

from backend.app.audit.models import AuditRecord, ExecutionState
from backend.app.audit.recorder import AuditRecorder
from backend.app.intelligence import MerchantIntelligence


def make_event(
    transaction_id: str,
    state: ExecutionState,
    amount: float,
    failure_message: str | None = None,
) -> AuditRecord:
    return AuditRecord(
        transaction_id=transaction_id,
        agent_id="buyer-1",
        model_version="test-v1",
        prompt_hash="test-hash",
        session_id=transaction_id,
        timestamp_utc=datetime.now(timezone.utc),
        requested_amount=amount,
        currency="USD",
        payment_method="test",
        execution_state=state,
        failure_message=failure_message,
    )


def test_merchant_intelligence_aggregates_transaction_outcomes():
    recorder = AuditRecorder()

    recorder.record(
        make_event(
            "tx-1",
            ExecutionState.CAPTURED,
            400.0,
        )
    )

    recorder.record(
        make_event(
            "tx-2",
            ExecutionState.BLOCKED,
            900.0,
            "RESTRICTED_CATEGORY",
        )
    )

    recorder.record(
        make_event(
            "tx-3",
            ExecutionState.FAILED,
            200.0,
            "Payment failed",
        )
    )

    insights = MerchantIntelligence(recorder).analyze()

    assert insights.total_events == 3
    assert insights.unique_transactions == 3
    assert insights.captured_transactions == 1
    assert insights.blocked_transactions == 1
    assert insights.failed_transactions == 1
    assert insights.approval_rate == 33.33
    assert insights.total_captured_value == 400.0
    assert insights.block_reasons == {
        "RESTRICTED_CATEGORY": 1,
    }


def test_merchant_intelligence_handles_empty_recorder():
    recorder = AuditRecorder()

    insights = MerchantIntelligence(recorder).analyze()

    assert insights.total_events == 0
    assert insights.unique_transactions == 0
    assert insights.captured_transactions == 0
    assert insights.blocked_transactions == 0
    assert insights.failed_transactions == 0
    assert insights.approval_rate == 0.0
    assert insights.total_captured_value == 0.0
    assert insights.block_reasons == {}


def test_merchant_intelligence_counts_duplicate_transaction_events_once():
    recorder = AuditRecorder()

    recorder.record(
        make_event(
            "tx-1",
            ExecutionState.PENDING,
            400.0,
        )
    )

    recorder.record(
        make_event(
            "tx-1",
            ExecutionState.CAPTURED,
            400.0,
        )
    )

    insights = MerchantIntelligence(recorder).analyze()

    assert insights.total_events == 2
    assert insights.unique_transactions == 1
    assert insights.captured_transactions == 1
    assert insights.total_captured_value == 400.0