from fastapi.testclient import TestClient

from backend.app.audit.recorder import AuditRecorder
from backend.app.audit.store import AuditStore
from backend.app.idempotency.store import idempotency_store
from backend.app.main import app


client = TestClient(app)


def valid_payload(
    transaction_id: str = "m14-e2e-001",
) -> dict[str, object]:
    return {
        "transaction_id": transaction_id,
        "buyer_id": "buyer-e2e-001",
        "quantity": 1,
        "max_budget": 500.0,
        "currency": "INR",
        "minimum_refund_days": 7,
        "seller_id": "seller-e2e-001",
        "unit_price": 100.0,
        "seller_currency": "INR",
        "refund_days": 7,
        "terms": "Standard purchase terms",
        "max_rounds": 3,
    }


def test_complete_transaction_pipeline():
    idempotency_store.clear()

    transaction_id = "m14-e2e-001"
    idempotency_key = "m14-e2e-complete"

    headers = {
        "X-API-Key": "buyer-demo-key",
        "Idempotency-Key": idempotency_key,
    }

    response = client.post(
        "/transactions",
        json=valid_payload(transaction_id),
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    # Authentication + transaction execution
    assert data["transaction"]["transaction_id"] == transaction_id

    # Negotiation completed
    assert data["negotiation_status"] == "ACCEPTED"

    # Policy + payment succeeded
    assert data["policy_result"]["approved"] is True
    assert data["payment_status"] == "CAPTURED"

    # Idempotency record completed
    key = f"transaction:buyer-demo-key:{idempotency_key}"
    record = idempotency_store.get(key)

    assert record is not None
    assert record.status == "COMPLETED"

    # Replay must return the exact cached result
    replay = client.post(
        "/transactions",
        json=valid_payload(transaction_id),
        headers=headers,
    )

    assert replay.status_code == 200
    assert replay.json() == data


def test_audit_recorder_persists_and_verifies_chain(tmp_path):
    audit_path = tmp_path / "audit_events.jsonl"

    store = AuditStore(audit_path)
    recorder = AuditRecorder(store=store)

    from backend.app.audit.models import AuditRecord, ExecutionState

    record = AuditRecord(
        transaction_id="m14-audit-001",
        agent_id="buyer-e2e-001",
        model_version="deterministic-v1",
        prompt_hash="not-recorded",
        session_id="m14-audit-001",
        timestamp_utc=__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ),
        requested_amount=100.0,
        currency="INR",
        payment_method="not-specified",
        execution_state=ExecutionState.CAPTURED,
        failure_message=None,
    )

    recorder.record(record)

    assert recorder.verify_chain() is True
    assert recorder.verify_persisted_chain() is True

    persisted = store.get_events("m14-audit-001")

    assert len(persisted) == 1
    assert persisted[0].event_hash == recorder.all_events()[0].event_hash