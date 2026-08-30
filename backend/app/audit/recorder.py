import hashlib
import json
from copy import deepcopy

from backend.app.audit.models import AuditRecord


class AuditRecorder:
    """In-memory append-only recorder for validated audit events."""

    def __init__(self) -> None:
        self._events: list[AuditRecord] = []

    def record(self, audit_record: AuditRecord) -> AuditRecord:
        """Record an audit event without mutating the caller's record."""
        if not isinstance(audit_record, AuditRecord):
            raise TypeError("audit_record must be an AuditRecord")

        # Work on a deep copy so the caller's object remains unchanged.
        recorded= deepcopy(audit_record)

        # Link this event to the previous event in the append-only chain.
        recorded.previous_event_hash = (
        self._events[-1].event_hash if self._events else None
       )

        # Calculate the hash after setting previous_event_hash.
        recorded.event_hash = self._compute_event_hash(recorded)

        self._events.append(recorded)
        return recorded

    @staticmethod
    def _compute_event_hash(audit_record: AuditRecord) -> str:
        """Create a deterministic SHA-256 hash for an audit event."""
        data = audit_record.model_dump(
            exclude={"event_hash"},
            mode="json",
        )

        canonical_data = json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return hashlib.sha256(canonical_data).hexdigest()

    def verify_chain(self) -> bool:
        """Verify that every recorded event belongs to an intact hash chain."""
        previous_hash = None

        for event in self._events:
            # The first event must not reference a previous event.
            if event.previous_event_hash != previous_hash:
                return False

            # Recalculate the event hash from its contents.
            expected_hash = self._compute_event_hash(event)

            if event.event_hash != expected_hash:
                return False

            previous_hash = event.event_hash

        return True

    def get_events(self, transaction_id: str) -> list[AuditRecord]:
        """Return recorded events belonging to one transaction."""
        if not transaction_id:
            raise ValueError("transaction_id must be non-empty")

        return [
            event
            for event in self._events
            if event.transaction_id == transaction_id
        ]

    def all_events(self) -> list[AuditRecord]:
        """Return all recorded events in insertion order."""
        return list(self._events)