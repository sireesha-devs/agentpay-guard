from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, validator


class ExecutionState(str, Enum):
    """The recorded state of a transaction execution attempt."""

    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class AuditRecord(BaseModel):
    """A validated, serializable audit event data contract."""

    transaction_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    prompt_hash: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    timestamp_utc: datetime

    requested_amount: float = Field(gt=0)
    currency: str = Field(min_length=1)
    payment_method: str = Field(min_length=1)
    gateway_order_id: Optional[str] = Field(default=None, min_length=1)
    gateway_payment_id: Optional[str] = Field(default=None, min_length=1)

    signature_valid: Optional[bool] = None
    payload_hash: Optional[str] = Field(default=None, min_length=1)
    destination_endpoint: Optional[str] = Field(default=None, min_length=1)

    execution_state: ExecutionState
    gateway_response_code: Optional[str] = Field(default=None, min_length=1)
    failure_message: Optional[str] = Field(default=None, min_length=1)

    intent_amount: Optional[float] = Field(default=None, gt=0)
    intent_currency: Optional[str] = Field(default=None, min_length=1)
    action_amount: Optional[float] = Field(default=None, gt=0)
    action_currency: Optional[str] = Field(default=None, min_length=1)
    alignment_score: Optional[float] = Field(default=None, ge=0, le=1)

    source_trusted: Optional[bool] = None
    injection_detected: Optional[bool] = None
    injection_risk_score: Optional[float] = Field(default=None, ge=0, le=1)
    injection_reason: Optional[str] = Field(default=None, min_length=1)

    hitl_required: Optional[bool] = None
    hitl_approval_status: Optional[str] = Field(default=None, min_length=1)

    previous_event_hash: Optional[str] = Field(default=None, min_length=1)
    event_hash: Optional[str] = Field(default=None, min_length=1)

    @validator("timestamp_utc")
    def timestamp_must_be_utc(cls, value: datetime) -> datetime:
        """Ensure timestamps are timezone-aware and use a zero UTC offset."""
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("timestamp_utc must be a UTC timestamp")
        return value
