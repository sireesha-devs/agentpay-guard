import pytest

from backend.app.guards.budget import BudgetGuard


def test_budget_guard_starts_with_zero_spending():
    guard = BudgetGuard(50000.0)

    assert guard.budget_limit == 50000.0
    assert guard.spent_amount == 0.0
    assert guard.remaining_budget() == 50000.0


def test_can_spend_within_budget():
    guard = BudgetGuard(50000.0)

    assert guard.can_spend(5000.0) is True


def test_cannot_spend_beyond_budget():
    guard = BudgetGuard(50000.0)

    assert guard.can_spend(50001.0) is False


def test_record_spend_updates_spending():
    guard = BudgetGuard(50000.0)

    guard.record_spend(5000.0)

    assert guard.spent_amount == 5000.0
    assert guard.remaining_budget() == 45000.0


def test_multiple_spends_accumulate():
    guard = BudgetGuard(50000.0)

    guard.record_spend(30000.0)
    guard.record_spend(10000.0)

    assert guard.spent_amount == 40000.0
    assert guard.remaining_budget() == 10000.0


def test_exact_budget_is_allowed():
    guard = BudgetGuard(50000.0)

    assert guard.can_spend(50000.0) is True

    guard.record_spend(50000.0)

    assert guard.remaining_budget() == 0.0


def test_exceeding_budget_raises_when_recording_spend():
    guard = BudgetGuard(50000.0)

    guard.record_spend(48000.0)

    with pytest.raises(ValueError):
        guard.record_spend(3000.0)


def test_invalid_budget_limit_is_rejected():
    with pytest.raises(ValueError):
        BudgetGuard(0)


def test_invalid_spend_amount_is_rejected():
    guard = BudgetGuard(50000.0)

    with pytest.raises(ValueError):
        guard.can_spend(0)

    with pytest.raises(ValueError):
        guard.record_spend(-100.0)


def test_reset_clears_spending():
    guard = BudgetGuard(50000.0)

    guard.record_spend(4000.0)
    guard.reset()

    assert guard.spent_amount == 0.0
    assert guard.remaining_budget() == 50000.0