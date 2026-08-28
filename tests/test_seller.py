import pytest
from pydantic import ValidationError

from backend.app.agents.seller import SellerAgent
from backend.app.models.transaction import Offer, PurchaseRequest


def create_purchase_request() -> PurchaseRequest:
    return PurchaseRequest(
        buyer_id="buyer-1",
        quantity=3,
        max_budget=300.0,
        currency="INR",
        minimum_refund_days=7,
    )


def test_valid_seller_agent_creates_expected_offer():
    agent = SellerAgent(
        seller_id="seller-1",
        unit_price=75.0,
        refund_days=14,
        currency="INR",
        terms="Standard return policy",
    )

    offer = agent.create_offer(create_purchase_request())

    assert isinstance(offer, Offer)
    assert offer.seller_id == "seller-1"
    assert offer.quantity == 3
    assert offer.unit_price == 75.0
    assert offer.currency == "INR"
    assert offer.refund_days == 14
    assert offer.terms == "Standard return policy"


def test_seller_agent_with_zero_unit_price_raises_validation_error():
    agent = SellerAgent(
        seller_id="seller-1",
        unit_price=0,
        refund_days=14,
        currency="INR",
        terms="Standard return policy",
    )

    with pytest.raises(ValidationError):
        agent.create_offer(create_purchase_request())


def test_seller_agent_with_negative_refund_days_raises_validation_error():
    agent = SellerAgent(
        seller_id="seller-1",
        unit_price=75.0,
        refund_days=-1,
        currency="INR",
        terms="Standard return policy",
    )

    with pytest.raises(ValidationError):
        agent.create_offer(create_purchase_request())
