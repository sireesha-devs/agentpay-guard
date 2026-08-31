from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone


class VelocityGuard:
    """Limits how many transactions an agent can perform within a time window."""

    def __init__(self, max_transactions: int, window_seconds: int) -> None:
        if max_transactions <= 0:
            raise ValueError("max_transactions must be greater than zero")

        if window_seconds <= 0:
            raise ValueError("window_seconds must be greater than zero")

        self.max_transactions = max_transactions
        self.window_seconds = window_seconds

        self._transactions: dict[str, deque[datetime]] = defaultdict(deque)

    def _remove_expired(
        self,
        agent_id: str,
        now: datetime,
    ) -> None:
        """Remove transaction timestamps outside the active time window."""
        cutoff = now - timedelta(seconds=self.window_seconds)

        timestamps = self._transactions[agent_id]

        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

    def can_execute(
        self,
        agent_id: str,
        now: datetime | None = None,
    ) -> bool:
        """Return True when the agent is below its transaction velocity limit."""
        if not agent_id:
            raise ValueError("agent_id must be non-empty")

        current_time = now or datetime.now(timezone.utc)

        if current_time.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        self._remove_expired(agent_id, current_time)

        return len(self._transactions[agent_id]) < self.max_transactions

    def record_execution(
        self,
        agent_id: str,
        now: datetime | None = None,
    ) -> None:
        """Record a transaction execution if the velocity limit allows it."""
        if not agent_id:
            raise ValueError("agent_id must be non-empty")

        current_time = now or datetime.now(timezone.utc)

        if current_time.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        if not self.can_execute(agent_id, current_time):
            raise ValueError(
                f"Velocity limit exceeded: maximum of "
                f"{self.max_transactions} transactions allowed within "
                f"{self.window_seconds} seconds."
            )

        self._transactions[agent_id].append(current_time)

    def current_count(
        self,
        agent_id: str,
        now: datetime | None = None,
    ) -> int:
        """Return the number of transactions currently inside the time window."""
        if not agent_id:
            raise ValueError("agent_id must be non-empty")

        current_time = now or datetime.now(timezone.utc)

        if current_time.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        self._remove_expired(agent_id, current_time)

        return len(self._transactions[agent_id])

    def reset(self, agent_id: str) -> None:
        """Clear the recorded transaction history for one agent."""
        if not agent_id:
            raise ValueError("agent_id must be non-empty")

        self._transactions.pop(agent_id, None)