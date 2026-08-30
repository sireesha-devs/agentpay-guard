class BudgetGuard:
    """Enforces a maximum cumulative spending limit."""

    def __init__(self, budget_limit: float) -> None:
        if budget_limit <= 0:
            raise ValueError("budget_limit must be greater than 0")

        self._budget_limit = budget_limit
        self._spent_amount = 0.0

    @property
    def budget_limit(self) -> float:
        """Return the configured spending limit."""
        return self._budget_limit

    @property
    def spent_amount(self) -> float:
        """Return the amount already spent."""
        return self._spent_amount

    def remaining_budget(self) -> float:
        """Return the amount that can still be spent."""
        return self._budget_limit - self._spent_amount

    def can_spend(self, amount: float) -> bool:
        """Return True when the requested amount stays within the budget."""
        if amount <= 0:
            raise ValueError("amount must be greater than 0")

        return self._spent_amount + amount <= self._budget_limit

    def record_spend(self, amount: float) -> None:
        """Record a successful spend."""
        if amount <= 0:
            raise ValueError("amount must be greater than 0")

        if not self.can_spend(amount):
            raise ValueError("spending amount exceeds remaining budget")

        self._spent_amount += amount

    def reset(self) -> None:
        """Reset cumulative spending to zero."""
        self._spent_amount = 0.0