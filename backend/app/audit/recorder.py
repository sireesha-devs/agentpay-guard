from backend.app.audit.models import AuditRecord


class AuditRecorder:
    """In-memory append-only recorder for validated audit events."""

    def __init__(self) -> None:
        self._events: list[AuditRecord] = []

    def record(self, audit_record: AuditRecord) -> AuditRecord:
        """Record one validated audit event and return the same record."""
        if not isinstance(audit_record, AuditRecord):
            raise TypeError("audit_record must be an AuditRecord")

        self._events.append(audit_record)
        return audit_record

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