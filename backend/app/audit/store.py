from __future__ import annotations
import os
import json
from pathlib import Path
from threading import Lock
from typing import List, Optional

from backend.app.audit.models import AuditRecord


class AuditStore:
    """
    File-backed append-only audit store.

    The store keeps one JSON object per line. Existing AuditRecorder
    remains responsible for constructing the tamper-evident hash chain;
    this class is responsible for durable persistence and retrieval.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        configured_path = path or os.getenv("AGENTPAY_AUDIT_PATH") or "data/audit_events.jsonl"
        self._path = Path(configured_path)
        self._lock = Lock()

        self._path.parent.mkdir(parents=True, exist_ok=True)

        if not self._path.exists():
            self._path.touch()

    @property
    def path(self) -> Path:
        return self._path

    def append(self, record: AuditRecord) -> AuditRecord:
        """Persist one validated audit record."""
        if not isinstance(record, AuditRecord):
            raise TypeError("record must be an AuditRecord")

        data = record.model_dump(mode="json")

        with self._lock:
            with self._path.open("a", encoding="utf-8") as file:
                file.write(
                    json.dumps(
                        data,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )
                file.write("\n")

        return record

    def all_events(self) -> List[AuditRecord]:
        """Load every persisted audit event in insertion order."""
        events: List[AuditRecord] = []

        if not self._path.exists():
            return events

        with self._lock:
            with self._path.open("r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()

                    if not line:
                        continue

                    events.append(
                        AuditRecord.model_validate(json.loads(line))
                    )

        return events

    def get_events(self, transaction_id: str) -> List[AuditRecord]:
        """Return all audit events belonging to a transaction."""
        if not transaction_id:
            raise ValueError("transaction_id must be non-empty")

        return [
            event
            for event in self.all_events()
            if event.transaction_id == transaction_id
        ]

    def get_latest(self, transaction_id: str) -> Optional[AuditRecord]:
        """Return the latest audit event for a transaction."""
        events = self.get_events(transaction_id)

        if not events:
            return None

        return events[-1]

    def count(self) -> int:
        """Return the number of persisted events."""
        return len(self.all_events())

    def clear(self) -> None:
        """
        Clear persisted events.

        Intended for tests/local development only.
        """
        with self._lock:
            self._path.write_text("", encoding="utf-8")
