import pytest
from pydantic import ValidationError

from backend.app.agents.buyer import BuyerAgent
from backend.app.models.transaction import PurchaseRequest


def test_valid_buyer_agent_creates_expected_purchase_request():
    agent = BuyerAgent(
        buyer_id="buyer-1",
        quantity=2,
        max_budget=100.0,
        currency="INR",
        minimum_refund_days=7,
    )

    purchase_request = agent.create_purchase_request()

    assert isinstance(purchase_request, PurchaseRequest)
    assert purchase_request.buyer_id == "buyer-1"
    assert purchase_request.quantity == 2
    assert purchase_request.max_budget == 100.0
    assert purchase_request.currency == "INR"
    assert purchase_request.minimum_refund_days == 7


def test_buyer_agent_with_zero_quantity_raises_validation_error():
    agent = BuyerAgent(
        buyer_id="buyer-1",
        quantity=0,
        max_budget=100.0,
        currency="INR",
        minimum_refund_days=7,
    )

    with pytest.raises(ValidationError):
        agent.create_purchase_request()


def test_buyer_agent_with_negative_max_budget_raises_validation_error():
    agent = BuyerAgent(
        buyer_id="buyer-1",
        quantity=2,
        max_budget=-100.0,
        currency="INR",
        minimum_refund_days=7,
    )

    with pytest.raises(ValidationError):
        agent.create_purchase_request()


def test_buyer_agent_with_negative_minimum_refund_days_raises_validation_error():
    agent = BuyerAgent(
        buyer_id="buyer-1",
        quantity=2,
        max_budget=100.0,
        currency="INR",
        minimum_refund_days=-1,
    )

    with pytest.raises(ValidationError):
        agent.create_purchase_request()
