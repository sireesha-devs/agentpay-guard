from __future__ import annotations

from pydantic import BaseModel, Field

from backend.app.guards.pipeline import GuardPipelineResult


class AIDecision(BaseModel):
    """Structured, explainable decision produced from deterministic guards."""

    decision: str
    risk_score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    risk_factors: list[str]
    recommended_action: str


class AIDecisionEngine:
    """Converts deterministic guard outcomes into explainable AI decisions."""

    _RISK_SCORES = {
        "BUDGET_EXCEEDED": 90,
        "VELOCITY_LIMIT_EXCEEDED": 85,
        "MERCHANT_NOT_ALLOWED": 95,
        "RESTRICTED_CATEGORY": 95,
        "AMOUNT_EXCEEDS_RISK_LIMIT": 90,
        "HIGH_VALUE_TRANSACTION": 60,
        "RISK_CHECK_PASSED": 10,
    }

    _ACTIONS = {
        "ALLOWED": "PROCEED_WITH_PAYMENT",
        "BLOCKED": "REJECT_TRANSACTION",
    }

    def evaluate(self, guard_result: GuardPipelineResult) -> AIDecision:
        """Generate an explainable decision without overriding guard controls."""

        failed_checks = [
            check for check in guard_result.checks
            if not check.passed
        ]

        if not guard_result.allowed:
            risk_factors = [
                check.reason_code
                for check in failed_checks
            ]

            primary_code = (
                risk_factors[0]
                if risk_factors
                else "GUARD_PIPELINE_BLOCKED"
            )

            risk_score = self._RISK_SCORES.get(primary_code, 90)

            reasoning = (
                "Transaction was blocked by the deterministic guard pipeline. "
                f"Primary risk factor: {primary_code}. "
                "The AI decision layer cannot override this safety control."
            )

            return AIDecision(
                decision="BLOCK",
                risk_score=risk_score,
                confidence=0.99,
                reasoning=reasoning,
                risk_factors=risk_factors or [primary_code],
                recommended_action=self._ACTIONS["BLOCKED"],
            )

        return AIDecision(
            decision="APPROVE",
            risk_score=self._RISK_SCORES["RISK_CHECK_PASSED"],
            confidence=0.99,
            reasoning=(
                "All deterministic transaction guards passed. "
                "No blocking risk factors were detected."
            ),
            risk_factors=[],
            recommended_action=self._ACTIONS["ALLOWED"],
        )
