import pytest
from backend.app.agents.buyer import BuyerAgent
from backend.app.agents.seller import SellerAgent
from backend.app.agents.commerce import CommerceAgent
from backend.app.models.transaction import Offer, PurchaseRequest


def make_request() -> PurchaseRequest:
    return PurchaseRequest(
        buyer_id="buyer-1",
        quantity=2,
        max_budget=1000.0,
        currency="USD",
        minimum_refund_days=7,
    )


def make_offer(
    unit_price: float = 400.0,
    quantity: int = 2,
    currency: str = "USD",
    refund_days: int = 14,
) -> Offer:
    return Offer(
        seller_id="seller-1",
        quantity=quantity,
        unit_price=unit_price,
        currency=currency,
        refund_days=refund_days,
        terms="Standard terms",
    )


def test_agent_approves_valid_offer():
    agent = CommerceAgent()

    decision = agent.evaluate_offer(
        make_request(),
        make_offer(),
    )

    assert decision.approved is True
    assert decision.total_cost == 800.0
    assert decision.rounds_used == 1


def test_agent_rejects_offer_over_budget():
    agent = CommerceAgent()

    decision = agent.evaluate_offer(
        make_request(),
        make_offer(unit_price=600.0),
    )

    assert decision.approved is False
    assert "budget" in decision.reason.lower()
    assert decision.total_cost == 1200.0


def test_agent_rejects_invalid_refund_terms():
    agent = CommerceAgent()

    decision = agent.evaluate_offer(
        make_request(),
        make_offer(refund_days=3),
    )

    assert decision.approved is False
    assert "refund" in decision.reason.lower()


def test_agent_rejects_currency_mismatch():
    agent = CommerceAgent()

    decision = agent.evaluate_offer(
        make_request(),
        make_offer(currency="EUR"),
    )

    assert decision.approved is False
    assert "currency" in decision.reason.lower()


def test_agent_rejects_quantity_mismatch():
    agent = CommerceAgent()

    decision = agent.evaluate_offer(
        make_request(),
        make_offer(quantity=1),
    )

    assert decision.approved is False
    assert "quantity" in decision.reason.lower()


def test_agent_enforces_maximum_rounds():
    agent = CommerceAgent(max_rounds=3)

    decision = agent.evaluate_offer(
        make_request(),
        make_offer(),
        rounds_used=4,
    )

    assert decision.approved is False
    assert decision.rounds_used == 3
    assert "rounds" in decision.reason.lower()


def test_invalid_max_rounds_is_rejected():
    with pytest.raises(ValueError):
        CommerceAgent(max_rounds=0)

def test_commerce_agent_orchestrates_buyer_and_seller():
    buyer = BuyerAgent(
        buyer_id="buyer-1",
        quantity=2,
        max_budget=1000.0,
        currency="USD",
        minimum_refund_days=7,
    )

    seller = SellerAgent(
        seller_id="seller-1",
        unit_price=400.0,
        refund_days=14,
        currency="USD",
        terms="Standard terms",
    )

    agent = CommerceAgent()

    decision = agent.negotiate(buyer, seller)

    assert decision.approved is True
    assert decision.total_cost == 800.0
    assert decision.purchase_request.buyer_id == "buyer-1"
    assert decision.offer.seller_id == "seller-1"


def test_commerce_agent_rejects_seller_offer_over_budget():
    buyer = BuyerAgent(
        buyer_id="buyer-1",
        quantity=2,
        max_budget=1000.0,
        currency="USD",
        minimum_refund_days=7,
    )

    seller = SellerAgent(
        seller_id="seller-1",
        unit_price=600.0,
        refund_days=14,
        currency="USD",
        terms="Standard terms",
    )

    agent = CommerceAgent()

    decision = agent.negotiate(buyer, seller)

    assert decision.approved is False
    assert decision.total_cost == 1200.0
    assert "budget" in decision.reason.lower()