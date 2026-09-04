from __future__ import annotations

from dataclasses import dataclass

from backend.app.ai.decision import AIDecision
from backend.app.guards.pipeline import GuardPipelineResult


@dataclass(frozen=True)
class GuardrailDecision:
    """Final safety decision after combining AI and deterministic controls."""

    allowed: bool
    decision: str
    reason: str
    ai_decision: str
    deterministic_disposition: str
    blocked_by: tuple[str, ...]


class GuardrailEngine:
    """Enforces the final safety boundary around AI transaction decisions.

    AI recommendations are advisory only. Deterministic guard failures
    always take precedence over an AI approval.
    """

    def evaluate(
        self,
        ai_decision: AIDecision,
        guard_result: GuardPipelineResult,
    ) -> GuardrailDecision:
        """Combine AI recommendation with deterministic guard results."""

        failed_checks = tuple(
            check.reason_code
            for check in guard_result.checks
            if not check.passed
        )

        if not guard_result.allowed:
            failed_reason = (
                failed_checks[0]
                if failed_checks
                else guard_result.final_disposition
            )

            return GuardrailDecision(
                allowed=False,
                decision="BLOCK",
                reason=(
                    "Transaction blocked by deterministic guardrail: "
                    f"{failed_reason}. AI decision cannot override "
                    "deterministic safety controls."
                ),
                ai_decision=ai_decision.decision,
                deterministic_disposition=guard_result.final_disposition,
                blocked_by=failed_checks,
            )

        if ai_decision.decision != "APPROVE":
            return GuardrailDecision(
                allowed=False,
                decision="BLOCK",
                reason=(
                    "Transaction was not approved by the AI decision engine."
                ),
                ai_decision=ai_decision.decision,
                deterministic_disposition=guard_result.final_disposition,
                blocked_by=(),
            )

        return GuardrailDecision(
            allowed=True,
            decision="APPROVE",
            reason=(
                "AI recommended approval and all deterministic "
                "guardrail checks passed."
            ),
            ai_decision=ai_decision.decision,
            deterministic_disposition=guard_result.final_disposition,
            blocked_by=(),
        )