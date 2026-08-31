from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from backend.app.guards.budget import BudgetGuard
from backend.app.guards.risk import RiskGuardEvaluator, TransactionPayload
from backend.app.guards.velocity import VelocityGuard


@dataclass(frozen=True)
class GuardCheckResult:
    """Result of one guard check."""

    guard_name: str
    passed: bool
    reason_code: str
    message: str


@dataclass(frozen=True)
class GuardPipelineResult:
    """Immutable result of the complete guard pipeline."""

    allowed: bool
    final_disposition: str
    checks: tuple[GuardCheckResult, ...]
    timestamp_utc: datetime


class GuardPipeline:
    """Runs budget, velocity, and risk checks before payment execution."""

    def __init__(
        self,
        budget_guard: BudgetGuard,
        velocity_guard: VelocityGuard,
        risk_evaluator: RiskGuardEvaluator,
    ) -> None:
        self._budget_guard = budget_guard
        self._velocity_guard = velocity_guard
        self._risk_evaluator = risk_evaluator

    def evaluate(
        self,
        payload: TransactionPayload,
        agent_id: str,
        now: Optional[datetime] = None,
    ) -> GuardPipelineResult:
        """Run guards in deterministic order and stop at the first failure."""

        current_time = now or datetime.now(timezone.utc)

        if current_time.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        checks: list[GuardCheckResult] = []

        amount = payload.amount

        if not self._budget_guard.can_spend(amount):
            checks.append(
                GuardCheckResult(
                    guard_name="budget",
                    passed=False,
                    reason_code="BUDGET_EXCEEDED",
                    message="Transaction exceeds the remaining budget.",
                )
            )
            return self._blocked_result(checks, current_time)

        checks.append(
            GuardCheckResult(
                guard_name="budget",
                passed=True,
                reason_code="BUDGET_OK",
                message="Transaction is within the remaining budget.",
            )
        )

        if not self._velocity_guard.can_execute(agent_id, current_time):
            checks.append(
                GuardCheckResult(
                    guard_name="velocity",
                    passed=False,
                    reason_code="VELOCITY_LIMIT_EXCEEDED",
                    message="Transaction velocity limit exceeded.",
                )
            )
            return self._blocked_result(checks, current_time)

        checks.append(
            GuardCheckResult(
                guard_name="velocity",
                passed=True,
                reason_code="VELOCITY_OK",
                message="Transaction velocity is within the configured limit.",
            )
        )

        risk_result = self._risk_evaluator.evaluate(payload)

        risk_allowed = risk_result.decision.value == "ALLOWED"

        risk_messages = {
           "RISK_CHECK_PASSED": "Risk checks passed.",
           "RESTRICTED_CATEGORY": "Transaction contains a restricted item category.",
           "MERCHANT_NOT_ALLOWED": "Merchant is not on the allowed merchant list.",
           "HIGH_RISK_SCORE": "Transaction risk score is too high.",
        }

        checks.append(
            GuardCheckResult(
                guard_name="risk",
                passed=risk_allowed,
                reason_code=risk_result.reason_code,
                message=risk_messages.get(
                   risk_result.reason_code,
                   "Transaction failed the risk check.",
                ),
            )
        )

        if risk_result.decision.value != "ALLOWED":
            return self._blocked_result(checks, current_time)

        return GuardPipelineResult(
            allowed=True,
            final_disposition="ALLOWED",
            checks=tuple(checks),
            timestamp_utc=current_time,
        )

    @staticmethod
    def _blocked_result(
        checks: list[GuardCheckResult],
        timestamp: datetime,
    ) -> GuardPipelineResult:
        """Build an immutable blocked pipeline result."""

        return GuardPipelineResult(
            allowed=False,
            final_disposition="BLOCKED",
            checks=tuple(checks),
            timestamp_utc=timestamp,
        )