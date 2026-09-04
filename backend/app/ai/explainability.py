from __future__ import annotations

from dataclasses import dataclass

from backend.app.ai.decision import AIDecision
from backend.app.guards.pipeline import GuardPipelineResult


@dataclass(frozen=True)
class RiskExplanation:
    """Human-readable explanation of an AI transaction decision."""

    decision: str
    risk_score: float
    confidence: float
    summary: str
    risk_factors: tuple[str, ...]
    guard_results: tuple[str, ...]
    recommended_action: str


class RiskExplainer:
    """Converts AI and deterministic guard results into an explainable decision."""

    def explain(
        self,
        ai_decision: AIDecision,
        guard_result: GuardPipelineResult,
    ) -> RiskExplanation:
        guard_results = tuple(
            f"{check.guard_name}: "
            f"{'PASSED' if check.passed else 'FAILED'} "
            f"({check.reason_code})"
            for check in guard_result.checks
        )

        if not guard_result.allowed:
            summary = (
                "Transaction blocked because a deterministic security "
                "guard failed. The AI decision cannot override this block."
            )
        elif ai_decision.decision == "APPROVE":
            summary = (
                "Transaction passed all deterministic guards and the AI "
                "decision recommends proceeding."
            )
        else:
            summary = (
                "Transaction passed deterministic guards, but the AI "
                "decision does not recommend proceeding."
            )

        return RiskExplanation(
            decision=ai_decision.decision,
            risk_score=ai_decision.risk_score,
            confidence=ai_decision.confidence,
            summary=summary,
            risk_factors=tuple(ai_decision.risk_factors),
            guard_results=guard_results,
            recommended_action=ai_decision.recommended_action,
        )