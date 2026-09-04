from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from backend.app.audit.models import AuditRecord, ExecutionState
from backend.app.audit.recorder import AuditRecorder


@dataclass(frozen=True)
class MerchantInsights:
    """Aggregated merchant-level transaction intelligence."""

    total_events: int
    unique_transactions: int
    captured_transactions: int
    blocked_transactions: int
    failed_transactions: int
    approval_rate: float
    total_captured_value: float
    block_reasons: dict[str, int]


class MerchantIntelligence:
    """Builds merchant insights from the existing audit trail."""

    def __init__(self, recorder: AuditRecorder) -> None:
        self._recorder = recorder

    def analyze(self) -> MerchantInsights:
        """Aggregate transaction outcomes from recorded audit events."""

        events = self._recorder.all_events()

        unique_transactions = {
            event.transaction_id
            for event in events
        }

        captured_events = [
            event
            for event in events
            if event.execution_state == ExecutionState.CAPTURED
        ]

        blocked_events = [
            event
            for event in events
            if event.execution_state == ExecutionState.BLOCKED
        ]

        failed_events = [
            event
            for event in events
            if event.execution_state == ExecutionState.FAILED
        ]

        completed_or_blocked = (
            len(captured_events)
            + len(blocked_events)
            + len(failed_events)
        )

        approval_rate = (
            len(captured_events) / completed_or_blocked * 100
            if completed_or_blocked
            else 0.0
        )

        total_captured_value = sum(
            event.requested_amount
            for event in captured_events
        )

        block_reasons = Counter(
            self._extract_block_reason(event)
            for event in blocked_events
        )

        return MerchantInsights(
            total_events=len(events),
            unique_transactions=len(unique_transactions),
            captured_transactions=len(captured_events),
            blocked_transactions=len(blocked_events),
            failed_transactions=len(failed_events),
            approval_rate=round(approval_rate, 2),
            total_captured_value=round(total_captured_value, 2),
            block_reasons=dict(block_reasons),
        )

    @staticmethod
    def _extract_block_reason(event: AuditRecord) -> str:
        """Extract a stable reason from a blocked audit event."""

        if event.failure_message:
            return event.failure_message

        return "UNKNOWN_BLOCK_REASON"