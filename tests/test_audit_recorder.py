from datetime import datetime, timezone

import pytest

from backend.app.audit.models import AuditRecord, ExecutionState
from backend.app.audit.recorder import AuditRecorder


def make_record(
    transaction_id: str = "transaction-1",
    agent_id: str = "agent-1",
) -> AuditRecord:
    return AuditRecord(
        transaction_id=transaction_id,
        agent_id=agent_id,
        model_version="model-v1",
        prompt_hash="prompt-hash-1",
        session_id="session-1",
        timestamp_utc=datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc),
        requested_amount=800.0,
        currency="INR",
        payment_method="card",
        execution_state=ExecutionState.CAPTURED,
    )


def test_record_one_event():
    recorder = AuditRecorder()
    record = make_record()

    result = recorder.record(record)

    assert result == record
    assert recorder.all_events() == [record]


def test_record_multiple_events():
    recorder = AuditRecorder()
    first = make_record("transaction-1", "agent-1")
    second = make_record("transaction-2", "agent-2")

    recorder.record(first)
    recorder.record(second)

    assert recorder.all_events() == [first, second]


def test_insertion_order_is_preserved():
    recorder = AuditRecorder()
    first = make_record("transaction-1")
    second = make_record("transaction-1")
    third = make_record("transaction-2")

    recorder.record(first)
    recorder.record(second)
    recorder.record(third)

    assert recorder.all_events() == [first, second, third]


def test_get_events_filters_by_transaction_id():
    recorder = AuditRecorder()
    first = make_record("transaction-1")
    second = make_record("transaction-2")
    third = make_record("transaction-1")

    recorder.record(first)
    recorder.record(second)
    recorder.record(third)

    assert recorder.get_events("transaction-1") == [first, third]


def test_get_events_returns_empty_for_unknown_transaction():
    recorder = AuditRecorder()

    assert recorder.get_events("unknown") == []


def test_all_events_returns_all_records():
    recorder = AuditRecorder()
    first = make_record("transaction-1")
    second = make_record("transaction-2")

    recorder.record(first)
    recorder.record(second)

    assert recorder.all_events() == [first, second]


def test_all_events_returns_copy():
    recorder = AuditRecorder()
    record = make_record()

    recorder.record(record)

    returned_events = recorder.all_events()
    returned_events.clear()

    assert recorder.all_events() == [record]


def test_get_events_returns_copy():
    recorder = AuditRecorder()
    record = make_record()

    recorder.record(record)

    returned_events = recorder.get_events("transaction-1")
    returned_events.clear()

    assert recorder.get_events("transaction-1") == [record]


def test_non_audit_record_input_raises_type_error():
    recorder = AuditRecorder()

    with pytest.raises(TypeError):
        recorder.record("not-an-audit-record")


def test_empty_transaction_id_raises_value_error():
    recorder = AuditRecorder()

    with pytest.raises(ValueError):
        recorder.get_events("")


def test_recorded_audit_record_is_not_modified():
    recorder = AuditRecorder()
    record = make_record()

    original = record.model_copy(deep=True)

    recorder.record(record)

    assert record == original


def test_records_from_different_transactions_remain_isolated():
    recorder = AuditRecorder()
    transaction_one = make_record("transaction-1")
    transaction_two = make_record("transaction-2")

    recorder.record(transaction_one)
    recorder.record(transaction_two)

    assert recorder.get_events("transaction-1") == [transaction_one]
    assert recorder.get_events("transaction-2") == [transaction_two]