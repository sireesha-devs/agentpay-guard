from datetime import datetime, timezone

from backend.app.audit.models import AuditRecord, ExecutionState
from backend.app.audit.recorder import AuditRecorder
from backend.app.audit.store import AuditStore


def make_record(transaction_id: str) -> AuditRecord:
    return AuditRecord(
        transaction_id=transaction_id,
        agent_id="agent-1",
        model_version="deterministic-v1",
        prompt_hash="prompt-hash",
        session_id="session-1",
        timestamp_utc=datetime(
            2026,
            8,
            31,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        requested_amount=500.0,
        currency="INR",
        payment_method="test",
        execution_state=ExecutionState.PENDING,
    )


def test_store_creates_file(tmp_path):
    store = AuditStore(tmp_path / "audit.jsonl")

    assert store.path.exists()


def test_store_persists_record(tmp_path):
    store = AuditStore(tmp_path / "audit.jsonl")

    record = make_record("tx-1")

    store.append(record)

    events = store.all_events()

    assert len(events) == 1
    assert events[0].transaction_id == "tx-1"


def test_store_filters_by_transaction(tmp_path):
    store = AuditStore(tmp_path / "audit.jsonl")

    store.append(make_record("tx-1"))
    store.append(make_record("tx-2"))

    events = store.get_events("tx-1")

    assert len(events) == 1
    assert events[0].transaction_id == "tx-1"


def test_store_returns_latest_event(tmp_path):
    store = AuditStore(tmp_path / "audit.jsonl")

    first = make_record("tx-1")
    second = make_record("tx-1")

    store.append(first)
    store.append(second)

    latest = store.get_latest("tx-1")

    assert latest is not None
    assert latest.transaction_id == "tx-1"


def test_store_count(tmp_path):
    store = AuditStore(tmp_path / "audit.jsonl")

    store.append(make_record("tx-1"))
    store.append(make_record("tx-2"))

    assert store.count() == 2


def test_store_clear(tmp_path):
    store = AuditStore(tmp_path / "audit.jsonl")

    store.append(make_record("tx-1"))

    store.clear()

    assert store.count() == 0


def test_recorder_persists_hash_chain(tmp_path):
    store = AuditStore(tmp_path / "audit.jsonl")
    recorder = AuditRecorder(store=store)

    recorder.record(make_record("tx-1"))
    recorder.record(make_record("tx-2"))

    assert recorder.verify_chain() is True
    assert recorder.verify_persisted_chain() is True

    events = store.all_events()

    assert len(events) == 2
    assert events[1].previous_event_hash == events[0].event_hash


def test_persisted_chain_detects_tampering(tmp_path):
    store = AuditStore(tmp_path / "audit.jsonl")
    recorder = AuditRecorder(store=store)

    recorder.record(make_record("tx-1"))
    recorder.record(make_record("tx-2"))

    lines = store.path.read_text(encoding="utf-8").splitlines()

    lines[0] = lines[0].replace(
        '"requested_amount":500.0',
        '"requested_amount":999.0',
    )

    store.path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    assert recorder.verify_persisted_chain() is False