import pytest
from pydantic import ValidationError

from backend.app.guards.risk import (
    RiskGuardEvaluator,
    RiskDecision,
    TransactionPayload,
)


def test_valid_payload_is_allowed():
    payload = TransactionPayload(
        amount=5000.0,
        currency="INR",
        merchant_id="merchant-001",
        item_category="electronics",
    )

    evaluator = RiskGuardEvaluator(
        allowed_merchants={"merchant-001"},
        restricted_categories={"weapons", "drugs"},
    )

    decision = evaluator.evaluate(payload)

    assert decision.decision == RiskDecision.ALLOWED
    assert decision.reason_code == "RISK_CHECK_PASSED"


def test_unknown_merchant_is_blocked():
    payload = TransactionPayload(
        amount=5000.0,
        currency="INR",
        merchant_id="merchant-999",
        item_category="electronics",
    )

    evaluator = RiskGuardEvaluator(
        allowed_merchants={"merchant-001"},
        restricted_categories={"weapons", "drugs"},
    )

    decision = evaluator.evaluate(payload)

    assert decision.decision == RiskDecision.BLOCKED
    assert decision.reason_code == "MERCHANT_NOT_ALLOWED"


def test_restricted_category_is_blocked():
    payload = TransactionPayload(
        amount=5000.0,
        currency="INR",
        merchant_id="merchant-001",
        item_category="weapons",
    )

    evaluator = RiskGuardEvaluator(
        allowed_merchants={"merchant-001"},
        restricted_categories={"weapons", "drugs"},
    )

    decision = evaluator.evaluate(payload)

    assert decision.decision == RiskDecision.BLOCKED
    assert decision.reason_code == "RESTRICTED_CATEGORY"


def test_high_amount_requires_challenge():
    payload = TransactionPayload(
        amount=40000.0,
        currency="INR",
        merchant_id="merchant-001",
        item_category="electronics",
    )

    evaluator = RiskGuardEvaluator(
        allowed_merchants={"merchant-001"},
        restricted_categories={"weapons", "drugs"},
        challenge_amount=30000.0,
    )

    decision = evaluator.evaluate(payload)

    assert decision.decision == RiskDecision.CHALLENGE
    assert decision.reason_code == "HIGH_VALUE_TRANSACTION"


def test_amount_above_maximum_is_blocked():
    payload = TransactionPayload(
        amount=60000.0,
        currency="INR",
        merchant_id="merchant-001",
        item_category="electronics",
    )

    evaluator = RiskGuardEvaluator(
        allowed_merchants={"merchant-001"},
        restricted_categories={"weapons", "drugs"},
        maximum_amount=50000.0,
    )

    decision = evaluator.evaluate(payload)

    assert decision.decision == RiskDecision.BLOCKED
    assert decision.reason_code == "AMOUNT_EXCEEDS_RISK_LIMIT"


def test_invalid_amount_is_rejected():
    with pytest.raises(ValidationError):
        TransactionPayload(
            amount=0,
            currency="INR",
            merchant_id="merchant-001",
            item_category="electronics",
        )


def test_invalid_currency_is_rejected():
    with pytest.raises(ValidationError):
        TransactionPayload(
            amount=5000.0,
            currency="",
            merchant_id="merchant-001",
            item_category="electronics",
        )


def test_invalid_merchant_id_is_rejected():
    with pytest.raises(ValidationError):
        TransactionPayload(
            amount=5000.0,
            currency="INR",
            merchant_id="",
            item_category="electronics",
        )


def test_invalid_item_category_is_rejected():
    with pytest.raises(ValidationError):
        TransactionPayload(
            amount=5000.0,
            currency="INR",
            merchant_id="merchant-001",
            item_category="",
        )


def test_currency_is_normalized():
    payload = TransactionPayload(
        amount=5000.0,
        currency="inr",
        merchant_id="merchant-001",
        item_category="electronics",
    )

    assert payload.currency == "INR"


def test_category_is_normalized():
    payload = TransactionPayload(
        amount=5000.0,
        currency="INR",
        merchant_id="merchant-001",
        item_category=" WEAPONS ",
    )

    assert payload.item_category == "weapons"

    evaluator = RiskGuardEvaluator(
        allowed_merchants={"merchant-001"},
        restricted_categories={"weapons"},
    )

    decision = evaluator.evaluate(payload)

    assert decision.decision == RiskDecision.BLOCKED
    assert decision.reason_code == "RESTRICTED_CATEGORY"


def test_evaluator_is_deterministic():
    payload = TransactionPayload(
        amount=5000.0,
        currency="INR",
        merchant_id="merchant-001",
        item_category="electronics",
    )

    evaluator = RiskGuardEvaluator(
        allowed_merchants={"merchant-001"},
        restricted_categories={"weapons", "drugs"},
    )

    first = evaluator.evaluate(payload)
    second = evaluator.evaluate(payload)

    assert first == second