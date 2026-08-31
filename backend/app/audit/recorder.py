import hashlib
import json
from copy import deepcopy
from typing import Optional

from backend.app.audit.models import AuditRecord
from backend.app.audit.store import AuditStore


class AuditRecorder:
    """
    Tamper-evident audit recorder.

    Events are kept in memory for fast access and optionally persisted
    through AuditStore for durability.
    """

    def __init__(
        self,
        store: Optional[AuditStore] = None,
    ) -> None:
        self._events: list[AuditRecord] = []
        self._store = store

    def record(self, audit_record: AuditRecord) -> AuditRecord:
        """Record and optionally persist one audit event."""
        if not isinstance(audit_record, AuditRecord):
            raise TypeError("audit_record must be an AuditRecord")

        recorded = deepcopy(audit_record)

        recorded.previous_event_hash = (
            self._events[-1].event_hash
            if self._events
            else None
        )

        recorded.event_hash = self._compute_event_hash(recorded)

        self._events.append(recorded)

        if self._store is not None:
            self._store.append(recorded)

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
        """Verify the in-memory audit hash chain."""
        previous_hash = None

        for event in self._events:
            if event.previous_event_hash != previous_hash:
                return False

            expected_hash = self._compute_event_hash(event)

            if event.event_hash != expected_hash:
                return False

            previous_hash = event.event_hash

        return True

    def verify_persisted_chain(self) -> bool:
        """Verify the persisted audit chain."""
        if self._store is None:
            return self.verify_chain()

        events = self._store.all_events()
        previous_hash = None

        for event in events:
            if event.previous_event_hash != previous_hash:
                return False

            expected_hash = self._compute_event_hash(event)

            if event.event_hash != expected_hash:
                return False

            previous_hash = event.event_hash

        return True

    def get_events(self, transaction_id: str) -> list[AuditRecord]:
        """Return in-memory events for a transaction."""
        if not transaction_id:
            raise ValueError("transaction_id must be non-empty")

        return [
            event
            for event in self._events
            if event.transaction_id == transaction_id
        ]

    def all_events(self) -> list[AuditRecord]:
        """Return all in-memory events in insertion order."""
        return list(self._events)

    def persisted_events(self) -> list[AuditRecord]:
        """Return all persisted events."""
        if self._store is None:
            return []

        return self._store.all_events()