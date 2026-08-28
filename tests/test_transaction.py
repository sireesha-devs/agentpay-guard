import pytest
from pydantic import ValidationError

from backend.app.models.transaction import (
    Offer,
    PolicyResult,
    PurchaseRequest,
    Transaction,
)


def test_valid_purchase_request_is_accepted():
    request = PurchaseRequest(
        buyer_id="buyer-1",
        quantity=2,
        max_budget=100.0,
        currency="INR",
        minimum_refund_days=7,
    )

    assert request.quantity == 2


def test_purchase_request_with_zero_quantity_is_rejected():
    with pytest.raises(ValidationError):
        PurchaseRequest(
            buyer_id="buyer-1",
            quantity=0,
            max_budget=100.0,
            currency="INR",
            minimum_refund_days=7,
        )


def test_purchase_request_with_negative_max_budget_is_rejected():
    with pytest.raises(ValidationError):
        PurchaseRequest(
            buyer_id="buyer-1",
            quantity=2,
            max_budget=-100.0,
            currency="INR",
            minimum_refund_days=7,
        )


def test_purchase_request_with_negative_minimum_refund_days_is_rejected():
    with pytest.raises(ValidationError):
        PurchaseRequest(
            buyer_id="buyer-1",
            quantity=2,
            max_budget=100.0,
            currency="INR",
            minimum_refund_days=-1,
        )


def test_valid_offer_is_accepted():
    offer = Offer(
        seller_id="seller-1",
        quantity=2,
        unit_price=45.0,
        currency="INR",
        refund_days=7,
        terms="Standard return policy",
    )

    assert offer.unit_price == 45.0


def test_offer_with_zero_unit_price_is_rejected():
    with pytest.raises(ValidationError):
        Offer(
            seller_id="seller-1",
            quantity=2,
            unit_price=0,
            currency="INR",
            refund_days=7,
            terms="Standard return policy",
        )


def test_offer_with_negative_refund_days_is_rejected():
    with pytest.raises(ValidationError):
        Offer(
            seller_id="seller-1",
            quantity=2,
            unit_price=45.0,
            currency="INR",
            refund_days=-1,
            terms="Standard return policy",
        )


def test_valid_transaction_with_nested_purchase_request_and_offer_is_accepted():
    purchase_request = PurchaseRequest(
        buyer_id="buyer-1",
        quantity=2,
        max_budget=100.0,
        currency="INR",
        minimum_refund_days=7,
    )
    offer = Offer(
        seller_id="seller-1",
        quantity=2,
        unit_price=45.0,
        currency="INR",
        refund_days=7,
        terms="Standard return policy",
    )

    transaction = Transaction(
        transaction_id="transaction-1",
        purchase_request=purchase_request,
        accepted_offer=offer,
        payment_status="pending",
    )

    assert transaction.purchase_request == purchase_request
    assert transaction.accepted_offer == offer


def test_policy_result_with_rejection_and_violation_is_accepted():
    result = PolicyResult(
        approved=False,
        reason="Budget exceeded",
        violations=["unit price exceeds budget"],
    )

    assert result.approved is False
    assert result.violations == ["unit price exceeds budget"]
