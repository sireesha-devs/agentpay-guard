import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from backend.app.audit.models import AuditRecord, ExecutionState


def complete_record_data() -> dict[str, object]:
    return {
        "transaction_id": "transaction-1",
        "agent_id": "buyer-agent-1",
        "model_version": "deterministic-v1",
        "prompt_hash": "prompt-hash-1",
        "session_id": "session-1",
        "timestamp_utc": datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc),
        "requested_amount": 800.0,
        "currency": "INR",
        "payment_method": "card",
        "gateway_order_id": "order-1",
        "gateway_payment_id": "payment-1",
        "signature_valid": True,
        "payload_hash": "payload-hash-1",
        "destination_endpoint": "/transactions",
        "execution_state": ExecutionState.CAPTURED,
        "gateway_response_code": "200",
        "intent_amount": 800.0,
        "intent_currency": "INR",
        "action_amount": 800.0,
        "action_currency": "INR",
        "alignment_score": 1.0,
        "source_trusted": True,
        "injection_detected": False,
        "injection_risk_score": 0.0,
        "hitl_required": False,
        "previous_event_hash": "previous-hash-1",
        "event_hash": "event-hash-1",
    }


def test_valid_complete_audit_record_can_be_created():
    record = AuditRecord(**complete_record_data())

    assert record.execution_state == ExecutionState.CAPTURED
    assert record.gateway_payment_id == "payment-1"


@pytest.mark.parametrize(
    "field",
    [
        "transaction_id",
        "agent_id",
        "model_version",
        "prompt_hash",
        "session_id",
        "timestamp_utc",
    ],
)
def test_required_identity_fields_are_enforced(field):
    record_data = complete_record_data()
    record_data.pop(field)

    with pytest.raises(ValidationError):
        AuditRecord(**record_data)


def test_utc_timestamp_is_accepted():
    record = AuditRecord(**complete_record_data())

    assert record.timestamp_utc.utcoffset() == timedelta(0)


def test_non_utc_timestamp_is_rejected():
    record_data = complete_record_data()
    record_data["timestamp_utc"] = datetime(
        2026,
        8,
        29,
        17,
        30,
        tzinfo=timezone(timedelta(hours=5, minutes=30)),
    )

    with pytest.raises(ValidationError):
        AuditRecord(**record_data)


def test_optional_gateway_fields_are_supported():
    record = AuditRecord(**complete_record_data())

    assert record.gateway_order_id == "order-1"
    assert record.gateway_payment_id == "payment-1"


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_alignment_score_rejects_values_outside_zero_to_one(score):
    record_data = complete_record_data()
    record_data["alignment_score"] = score

    with pytest.raises(ValidationError):
        AuditRecord(**record_data)


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_injection_risk_score_rejects_values_outside_zero_to_one(score):
    record_data = complete_record_data()
    record_data["injection_risk_score"] = score

    with pytest.raises(ValidationError):
        AuditRecord(**record_data)


def test_optional_security_fields_can_be_omitted():
    record_data = complete_record_data()
    for field in (
        "signature_valid",
        "payload_hash",
        "destination_endpoint",
        "source_trusted",
        "injection_detected",
        "injection_risk_score",
        "injection_reason",
    ):
        record_data.pop(field, None)

    record = AuditRecord(**record_data)

    assert record.signature_valid is None
    assert record.injection_risk_score is None


def test_execution_state_is_represented_by_enum():
    record = AuditRecord(**complete_record_data())

    assert record.execution_state == ExecutionState.CAPTURED
    assert record.execution_state.value == "CAPTURED"


def test_audit_record_serializes_to_json_compatible_structure():
    record = AuditRecord(**complete_record_data())
    serialized = json.loads(record.json())

    assert record.dict()["transaction_id"] == "transaction-1"
    assert serialized["timestamp_utc"] == "2026-08-29T12:00:00Z"
    assert serialized["execution_state"] == "CAPTURED"


def test_audit_record_is_deterministic_for_identical_input():
    record_data = complete_record_data()

    assert AuditRecord(**record_data) == AuditRecord(**record_data)
