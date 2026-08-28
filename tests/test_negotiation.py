import pytest

from backend.app.agents.seller import SellerAgent
from backend.app.models.transaction import Offer, PurchaseRequest
from backend.app.negotiation.engine import NegotiationEngine, NegotiationStatus


def create_purchase_request(
    quantity: int = 2,
    max_budget: float = 100.0,
    minimum_refund_days: int = 7,
) -> PurchaseRequest:
    return PurchaseRequest(
        buyer_id="buyer-1",
        quantity=quantity,
        max_budget=max_budget,
        currency="INR",
        minimum_refund_days=minimum_refund_days,
    )


def create_seller_agent(
    unit_price: float = 40.0,
    refund_days: int = 7,
) -> SellerAgent:
    return SellerAgent(
        seller_id="seller-1",
        unit_price=unit_price,
        refund_days=refund_days,
        currency="INR",
        terms="Standard return policy",
    )


def test_valid_seller_offer_is_accepted():
    engine = NegotiationEngine(
        create_purchase_request(),
        create_seller_agent(),
    )

    result = engine.negotiate()

    assert result.status == NegotiationStatus.ACCEPTED


def test_offer_exceeding_total_budget_returns_counter_offer():
    engine = NegotiationEngine(
        create_purchase_request(),
        create_seller_agent(unit_price=60.0),
    )

    result = engine.negotiate()

    assert result.status == NegotiationStatus.COUNTER_OFFER


def test_offer_with_insufficient_refund_days_returns_counter_offer():
    engine = NegotiationEngine(
        create_purchase_request(),
        create_seller_agent(refund_days=6),
    )

    result = engine.negotiate()

    assert result.status == NegotiationStatus.COUNTER_OFFER


def test_offer_with_incorrect_quantity_returns_counter_offer(monkeypatch):
    seller_agent = create_seller_agent()
    monkeypatch.setattr(
        seller_agent,
        "create_offer",
        lambda purchase_request: Offer(
            seller_id="seller-1",
            quantity=purchase_request.quantity + 1,
            unit_price=40.0,
            currency="INR",
            refund_days=7,
            terms="Standard return policy",
        ),
    )
    engine = NegotiationEngine(create_purchase_request(), seller_agent)

    result = engine.negotiate()

    assert result.status == NegotiationStatus.COUNTER_OFFER


def test_offer_with_multiple_violations_records_all_violations(monkeypatch):
    seller_agent = create_seller_agent()
    monkeypatch.setattr(
        seller_agent,
        "create_offer",
        lambda purchase_request: Offer(
            seller_id="seller-1",
            quantity=purchase_request.quantity + 1,
            unit_price=60.0,
            currency="INR",
            refund_days=6,
            terms="Standard return policy",
        ),
    )
    engine = NegotiationEngine(create_purchase_request(), seller_agent)

    result = engine.negotiate()
    history_entry = result.history[0]

    assert "does not match requested quantity" in history_entry
    assert "exceeds maximum budget" in history_entry
    assert "less than required minimum" in history_entry


def test_failed_fixed_offer_reaches_rejected_after_max_rounds():
    engine = NegotiationEngine(
        create_purchase_request(),
        create_seller_agent(unit_price=60.0),
        max_rounds=3,
    )

    engine.negotiate()
    engine.negotiate()
    result = engine.negotiate()

    assert result.status == NegotiationStatus.REJECTED
    assert result.rounds == 3


def test_history_contains_one_entry_per_attempted_round():
    engine = NegotiationEngine(
        create_purchase_request(),
        create_seller_agent(unit_price=60.0),
        max_rounds=3,
    )

    engine.negotiate()
    result = engine.negotiate()

    assert len(result.history) == 2
    assert result.history[0].startswith("Round 1:")
    assert result.history[1].startswith("Round 2:")


def test_zero_max_rounds_raises_value_error():
    with pytest.raises(ValueError):
        NegotiationEngine(
            create_purchase_request(),
            create_seller_agent(),
            max_rounds=0,
        )


def test_accepted_result_contains_accepted_offer():
    engine = NegotiationEngine(
        create_purchase_request(),
        create_seller_agent(),
    )

    result = engine.negotiate()

    assert result.accepted_offer is not None


def test_rejected_result_has_no_accepted_offer():
    engine = NegotiationEngine(
        create_purchase_request(),
        create_seller_agent(unit_price=60.0),
        max_rounds=3,
    )

    engine.negotiate()
    engine.negotiate()
    result = engine.negotiate()

    assert result.accepted_offer is None
