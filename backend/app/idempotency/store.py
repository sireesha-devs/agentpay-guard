from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class IdempotencyRecord:
    """Store the state and response associated with one idempotency key."""

    status: str
    response: Any = None


class IdempotencyStore:
    """Thread-safe process-local idempotency store."""

    def __init__(self) -> None:
        self._records: dict[str, IdempotencyRecord] = {}
        self._lock = Lock()

    def reserve(self, key: str) -> bool:
        """Atomically reserve an idempotency key."""
        if not key:
            raise ValueError("Idempotency key must be non-empty")

        with self._lock:
            if key in self._records:
                return False

            self._records[key] = IdempotencyRecord(status="PROCESSING")
            return True

    def complete(self, key: str, response: Any) -> None:
        """Store the completed response for an idempotency key."""
        with self._lock:
            record = self._records.get(key)

            if record is None:
                raise KeyError(f"Unknown idempotency key: {key}")

            record.status = "COMPLETED"
            record.response = response

    def get(self, key: str) -> IdempotencyRecord | None:
        """Return the record associated with a key."""
        with self._lock:
            return self._records.get(key)

    def remove(self, key: str) -> None:
        """Remove one idempotency key."""
        with self._lock:
            self._records.pop(key, None)

    def clear(self) -> None:
        """Clear all records. Intended for tests/local development."""
        with self._lock:
            self._records.clear()


idempotency_store = IdempotencyStore()
