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

   assert result.event_hash is not None
   assert result.previous_event_hash is None
   assert recorder.all_events()[0] == result


def test_record_multiple_events():
    recorder = AuditRecorder()
    first = make_record("transaction-1", "agent-1")
    second = make_record("transaction-2", "agent-2")

    first_recorded = recorder.record(first)
    second_recorded = recorder.record(second)

    events = recorder.all_events()

    assert len(events) == 2
    assert events[0] == first_recorded
    assert events[1] == second_recorded
    assert events[0].event_hash is not None
    assert events[1].event_hash is not None

def test_insertion_order_is_preserved():
    recorder = AuditRecorder()

    first = make_record("transaction-1")
    second = make_record("transaction-1")
    third = make_record("transaction-2")

    first_recorded = recorder.record(first)
    second_recorded = recorder.record(second)
    third_recorded = recorder.record(third)

    assert recorder.all_events() == [
        first_recorded,
        second_recorded,
        third_recorded,
    ]

def test_get_events_filters_by_transaction_id():
    recorder = AuditRecorder()

    first = make_record("transaction-1")
    second = make_record("transaction-2")
    third = make_record("transaction-1")

    first_recorded = recorder.record(first)
    recorder.record(second)
    third_recorded = recorder.record(third)

    assert recorder.get_events("transaction-1") == [
        first_recorded,
        third_recorded,
    ]

def test_get_events_returns_empty_for_unknown_transaction():
    recorder = AuditRecorder()

    assert recorder.get_events("unknown") == []


def test_all_events_returns_all_records():
    recorder = AuditRecorder()

    first = make_record("transaction-1")
    second = make_record("transaction-2")

    first_recorded = recorder.record(first)
    second_recorded = recorder.record(second)

    assert recorder.all_events() == [
        first_recorded,
        second_recorded,
    ]


def test_all_events_returns_copy():
    recorder = AuditRecorder()
    record = make_record()

    recorded = recorder.record(record)

    returned_events = recorder.all_events()
    returned_events.clear()

    assert recorder.all_events() == [recorded]


def test_get_events_returns_copy():
    recorder = AuditRecorder()
    record = make_record()

    recorded = recorder.record(record)

    returned_events = recorder.get_events("transaction-1")
    returned_events.clear()

    assert recorder.get_events("transaction-1") == [recorded]

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

    recorded_one = recorder.record(transaction_one)
    recorded_two = recorder.record(transaction_two)

    assert recorder.get_events("transaction-1") == [recorded_one]
    assert recorder.get_events("transaction-2") == [recorded_two]
def test_first_record_starts_hash_chain():
    recorder = AuditRecorder()

    recorded = recorder.record(make_record())

    assert recorded.previous_event_hash is None
    assert recorded.event_hash is not None
    assert len(recorded.event_hash) == 64


def test_second_record_points_to_first_event_hash():
    recorder = AuditRecorder()

    first = recorder.record(make_record("transaction-1"))
    second = recorder.record(make_record("transaction-2"))

    assert second.previous_event_hash == first.event_hash
    assert second.event_hash is not None
    assert second.event_hash != first.event_hash


def test_hash_chain_can_be_verified():
    recorder = AuditRecorder()

    recorder.record(make_record("transaction-1"))
    recorder.record(make_record("transaction-1"))
    recorder.record(make_record("transaction-2"))

    assert recorder.verify_chain() is True


def test_modified_event_breaks_hash_chain():
    recorder = AuditRecorder()

    recorder.record(make_record("transaction-1"))
    recorder.record(make_record("transaction-2"))

    recorder._events[0].requested_amount = 9999.0

    assert recorder.verify_chain() is False


def test_hash_is_deterministic_for_identical_records():
    first_recorder = AuditRecorder()
    second_recorder = AuditRecorder()

    first = first_recorder.record(make_record())
    second = second_recorder.record(make_record())

    assert first.event_hash == second.event_hash


def test_empty_recorder_has_valid_chain():
    recorder = AuditRecorder()

    assert recorder.verify_chain() is True


def test_chain_preserves_original_input_record():
    recorder = AuditRecorder()
    original = make_record()

    recorded = recorder.record(original)

    assert original.event_hash is None
    assert original.previous_event_hash is None
    assert recorded is not original