import pytest

from backend.app.models.transaction import Offer, PolicyResult, PurchaseRequest
from backend.app.policy.engine import PolicyEngine


@pytest.fixture
def purchase_request() -> PurchaseRequest:
    return PurchaseRequest(
        buyer_id="buyer-1",
        quantity=2,
        max_budget=1000.0,
        currency="INR",
        minimum_refund_days=7,
    )


def create_offer(
    quantity: int = 2,
    unit_price: float = 400.0,
    currency: str = "INR",
    refund_days: int = 7,
) -> Offer:
    return Offer(
        seller_id="seller-1",
        quantity=quantity,
        unit_price=unit_price,
        currency=currency,
        refund_days=refund_days,
        terms="Seven-day return policy",
    )


def test_valid_offer_passes_all_policy_checks(purchase_request):
    result = PolicyEngine().evaluate(purchase_request, create_offer())

    assert isinstance(result, PolicyResult)
    assert result.approved is True


def test_offer_exceeding_max_budget_is_rejected(purchase_request):
    result = PolicyEngine().evaluate(
        purchase_request,
        create_offer(unit_price=600.0),
    )

    assert result.approved is False


def test_offer_below_minimum_refund_days_is_rejected(purchase_request):
    result = PolicyEngine().evaluate(
        purchase_request,
        create_offer(refund_days=5),
    )

    assert result.approved is False


def test_offer_with_incorrect_quantity_is_rejected(purchase_request):
    result = PolicyEngine().evaluate(
        purchase_request,
        create_offer(quantity=3),
    )

    assert result.approved is False


def test_offer_with_different_currency_is_rejected(purchase_request):
    result = PolicyEngine().evaluate(
        purchase_request,
        create_offer(currency="USD"),
    )

    assert result.approved is False


def test_offer_with_multiple_violations_records_all_violations(purchase_request):
    result = PolicyEngine().evaluate(
        purchase_request,
        create_offer(
            quantity=3,
            unit_price=600.0,
            currency="USD",
            refund_days=5,
        ),
    )

    assert len(result.violations) == 4
    assert any("does not match requested quantity" in item for item in result.violations)
    assert any("exceeds maximum budget" in item for item in result.violations)
    assert any("less than minimum refund days" in item for item in result.violations)
    assert any("does not match requested currency" in item for item in result.violations)


def test_approved_policy_result_has_no_violations(purchase_request):
    result = PolicyEngine().evaluate(purchase_request, create_offer())

    assert result.approved is True
    assert result.violations == []


def test_rejected_policy_result_has_at_least_one_violation(purchase_request):
    result = PolicyEngine().evaluate(
        purchase_request,
        create_offer(unit_price=600.0),
    )

    assert result.approved is False
    assert result.violations
