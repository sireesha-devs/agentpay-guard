from enum import Enum

from pydantic import BaseModel, Field, field_validator


class RiskDecision(str, Enum):
    """Possible outcomes of the deterministic risk evaluation."""

    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    CHALLENGE = "CHALLENGE"


class TransactionPayload(BaseModel):
    """Validated transaction payload received from an agent."""

    amount: float = Field(gt=0)
    currency: str = Field(min_length=1)
    merchant_id: str = Field(min_length=1)
    item_category: str = Field(min_length=1)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        """Normalize currency codes to uppercase."""
        return value.strip().upper()

    @field_validator("merchant_id")
    @classmethod
    def normalize_merchant_id(cls, value: str) -> str:
        """Normalize merchant identifiers."""
        return value.strip()

    @field_validator("item_category")
    @classmethod
    def normalize_item_category(cls, value: str) -> str:
        """Normalize item categories."""
        return value.strip().lower()


class RiskDecisionResult(BaseModel):
    """Structured result returned by the risk evaluator."""

    decision: RiskDecision
    reason_code: str


class RiskGuardEvaluator:
    """Deterministically evaluates transaction risk."""

    def __init__(
        self,
        allowed_merchants: set[str],
        restricted_categories: set[str],
        challenge_amount: float = 30000.0,
        maximum_amount: float = 50000.0,
    ) -> None:
        if challenge_amount <= 0:
            raise ValueError("challenge_amount must be greater than zero")

        if maximum_amount <= 0:
            raise ValueError("maximum_amount must be greater than zero")

        if challenge_amount > maximum_amount:
            raise ValueError(
                "challenge_amount cannot be greater than maximum_amount"
            )

        self.allowed_merchants = {
            merchant.strip()
            for merchant in allowed_merchants
        }

        self.restricted_categories = {
            category.strip().lower()
            for category in restricted_categories
        }

        self.challenge_amount = challenge_amount
        self.maximum_amount = maximum_amount

    def evaluate(
        self,
        payload: TransactionPayload,
    ) -> RiskDecisionResult:
        """Evaluate a validated transaction payload against deterministic rules."""

        if payload.merchant_id not in self.allowed_merchants:
            return RiskDecisionResult(
                decision=RiskDecision.BLOCKED,
                reason_code="MERCHANT_NOT_ALLOWED",
            )

        if payload.item_category in self.restricted_categories:
            return RiskDecisionResult(
                decision=RiskDecision.BLOCKED,
                reason_code="RESTRICTED_CATEGORY",
            )

        if payload.amount > self.maximum_amount:
            return RiskDecisionResult(
                decision=RiskDecision.BLOCKED,
                reason_code="AMOUNT_EXCEEDS_RISK_LIMIT",
            )

        if payload.amount >= self.challenge_amount:
            return RiskDecisionResult(
                decision=RiskDecision.CHALLENGE,
                reason_code="HIGH_VALUE_TRANSACTION",
            )

        return RiskDecisionResult(
            decision=RiskDecision.ALLOWED,
            reason_code="RISK_CHECK_PASSED",
        )