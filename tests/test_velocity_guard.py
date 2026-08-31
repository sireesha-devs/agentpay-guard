from datetime import datetime, timedelta, timezone

import pytest

from backend.app.guards.velocity import VelocityGuard


def test_velocity_guard_starts_empty():
    guard = VelocityGuard(
        max_transactions=5,
        window_seconds=60,
    )

    now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

    assert guard.current_count("agent-1", now) == 0
    assert guard.can_execute("agent-1", now) is True


def test_transactions_within_limit_are_allowed():
    guard = VelocityGuard(
        max_transactions=5,
        window_seconds=60,
    )

    now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

    for offset in range(5):
        timestamp = now + timedelta(seconds=offset)
        assert guard.can_execute("agent-1", timestamp) is True
        guard.record_execution("agent-1", timestamp)

    assert guard.current_count(
        "agent-1",
        now + timedelta(seconds=4),
    ) == 5


def test_sixth_transaction_is_blocked():
    guard = VelocityGuard(
        max_transactions=5,
        window_seconds=60,
    )

    now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

    for offset in range(5):
        guard.record_execution(
            "agent-1",
            now + timedelta(seconds=offset),
        )

    assert guard.can_execute(
        "agent-1",
        now + timedelta(seconds=5),
    ) is False

    with pytest.raises(ValueError):
        guard.record_execution(
            "agent-1",
            now + timedelta(seconds=5),
        )


def test_expired_transaction_allows_new_execution():
    guard = VelocityGuard(
        max_transactions=5,
        window_seconds=60,
    )

    now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

    for offset in range(5):
        guard.record_execution(
            "agent-1",
            now + timedelta(seconds=offset),
        )

    after_window = now + timedelta(seconds=65)

    assert guard.can_execute("agent-1", after_window) is True

    guard.record_execution("agent-1", after_window)

    assert guard.current_count("agent-1", after_window) == 1


def test_agents_have_independent_velocity_limits():
    guard = VelocityGuard(
        max_transactions=2,
        window_seconds=60,
    )

    now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

    guard.record_execution("agent-1", now)
    guard.record_execution("agent-1", now + timedelta(seconds=1))

    assert guard.can_execute(
        "agent-1",
        now + timedelta(seconds=2),
    ) is False

    assert guard.can_execute(
        "agent-2",
        now + timedelta(seconds=2),
    ) is True


def test_current_count_ignores_expired_transactions():
    guard = VelocityGuard(
        max_transactions=5,
        window_seconds=60,
    )

    now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

    guard.record_execution("agent-1", now)
    guard.record_execution(
        "agent-1",
        now + timedelta(seconds=30),
    )

    assert guard.current_count(
        "agent-1",
        now + timedelta(seconds=30),
    ) == 2

    assert guard.current_count(
        "agent-1",
        now + timedelta(seconds=61),
    ) == 1


def test_reset_clears_agent_velocity_history():
    guard = VelocityGuard(
        max_transactions=5,
        window_seconds=60,
    )

    now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

    guard.record_execution("agent-1", now)
    guard.record_execution(
        "agent-1",
        now + timedelta(seconds=1),
    )

    assert guard.current_count(
        "agent-1",
        now + timedelta(seconds=1),
    ) == 2

    guard.reset("agent-1")

    assert guard.current_count(
        "agent-1",
        now + timedelta(seconds=1),
    ) == 0


def test_invalid_max_transactions_is_rejected():
    with pytest.raises(ValueError):
        VelocityGuard(
            max_transactions=0,
            window_seconds=60,
        )


def test_invalid_window_is_rejected():
    with pytest.raises(ValueError):
        VelocityGuard(
            max_transactions=5,
            window_seconds=0,
        )


def test_empty_agent_id_is_rejected():
    guard = VelocityGuard(
        max_transactions=5,
        window_seconds=60,
    )

    now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError):
        guard.can_execute("", now)

    with pytest.raises(ValueError):
        guard.record_execution("", now)

    with pytest.raises(ValueError):
        guard.current_count("", now)

    with pytest.raises(ValueError):
        guard.reset("")


def test_naive_datetime_is_rejected():
    guard = VelocityGuard(
        max_transactions=5,
        window_seconds=60,
    )

    naive_now = datetime(2026, 8, 31, 12, 0)

    with pytest.raises(ValueError):
        guard.can_execute("agent-1", naive_now)

    with pytest.raises(ValueError):
        guard.record_execution("agent-1", naive_now)

    with pytest.raises(ValueError):
        guard.current_count("agent-1", naive_now)