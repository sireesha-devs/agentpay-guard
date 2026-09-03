from datetime import datetime, timezone

from backend.app.audit.models import AuditRecord, ExecutionState
from backend.app.audit.recorder import AuditRecorder


def make_record(transaction_id: str) -> AuditRecord:
    return AuditRecord(
        transaction_id=transaction_id,
        agent_id="agent-1",
        model_version="test-v1",
        prompt_hash="prompt-hash",
        session_id="session-1",
        timestamp_utc=datetime.now(timezone.utc),
        requested_amount=100.0,
        currency="INR",
        payment_method="UPI",
        execution_state=ExecutionState.AUTHORIZED,
    )


def test_audit_chain_detects_event_tampering():
    recorder = AuditRecorder()

    recorder.record(make_record("transaction-1"))
    recorder.record(make_record("transaction-2"))

    assert recorder.verify_chain() is True

    # Tamper with an existing event after it has been hashed.
    recorder._events[0].requested_amount = 9999.0

    assert recorder.verify_chain() is False


def test_audit_chain_detects_previous_hash_tampering():
    recorder = AuditRecorder()

    recorder.record(make_record("transaction-1"))
    recorder.record(make_record("transaction-2"))

    assert recorder.verify_chain() is True

    # Break the chain link between the two events.
    recorder._events[1].previous_event_hash = "tampered-hash"

    assert recorder.verify_chain() is False