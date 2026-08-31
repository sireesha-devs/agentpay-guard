from backend.app.guards.budget import BudgetGuard
from backend.app.guards.velocity import VelocityGuard
import pytest

from backend.app.agents.buyer import BuyerAgent
from backend.app.agents.seller import SellerAgent
from backend.app.orchestration.service import AgentPayOrchestrator


@pytest.fixture
def buyer_agent() -> BuyerAgent:
    return BuyerAgent(
        buyer_id="buyer-1",
        quantity=2,
        max_budget=1000.0,
        currency="INR",
        minimum_refund_days=7,
    )


@pytest.fixture
def successful_seller_agent() -> SellerAgent:
    return SellerAgent(
        seller_id="seller-1",
        unit_price=400.0,
        refund_days=7,
        currency="INR",
        terms="Seven-day return policy",
    )


def test_complete_successful_flow_reaches_captured(buyer_agent, successful_seller_agent):
    result = AgentPayOrchestrator(buyer_agent, successful_seller_agent).run("tx-1")

    assert result.payment_status == "CAPTURED"


def test_successful_flow_has_expected_transaction_id(buyer_agent, successful_seller_agent):
    result = AgentPayOrchestrator(buyer_agent, successful_seller_agent).run("tx-expected")

    assert result.transaction.transaction_id == "tx-expected"


def test_successful_flow_contains_accepted_offer(buyer_agent, successful_seller_agent):
    result = AgentPayOrchestrator(buyer_agent, successful_seller_agent).run("tx-3")

    assert result.transaction.accepted_offer is not None


def test_successful_flow_contains_approved_policy_result(buyer_agent, successful_seller_agent):
    result = AgentPayOrchestrator(buyer_agent, successful_seller_agent).run("tx-4")

    assert result.policy_result.approved is True


def test_failed_negotiation_does_not_capture_payment(buyer_agent):
    seller_agent = SellerAgent(
        seller_id="seller-1",
        unit_price=600.0,
        refund_days=7,
        currency="INR",
        terms="Seven-day return policy",
    )

    result = AgentPayOrchestrator(buyer_agent, seller_agent).run("tx-5")

    assert result.payment_status == "failed"
    assert result.transaction.payment_status == "failed"


def test_failed_negotiation_produces_rejected_policy_result(buyer_agent):
    seller_agent = SellerAgent(
        seller_id="seller-1",
        unit_price=600.0,
        refund_days=7,
        currency="INR",
        terms="Seven-day return policy",
    )

    result = AgentPayOrchestrator(buyer_agent, seller_agent).run("tx-6")

    assert result.policy_result.approved is False


def test_policy_rejection_prevents_payment(buyer_agent):
    seller_agent = SellerAgent(
        seller_id="seller-1",
        unit_price=400.0,
        refund_days=7,
        currency="USD",
        terms="Seven-day return policy",
    )

    result = AgentPayOrchestrator(buyer_agent, seller_agent).run("tx-7")

    assert result.policy_result.approved is False
    assert result.payment_status == "failed"


def test_payment_is_captured_only_when_policy_is_approved(buyer_agent, successful_seller_agent):
    approved_result = AgentPayOrchestrator(
        buyer_agent,
        successful_seller_agent,
    ).run("tx-8")
    rejected_result = AgentPayOrchestrator(
        buyer_agent,
        SellerAgent(
            seller_id="seller-1",
            unit_price=400.0,
            refund_days=7,
            currency="USD",
            terms="Seven-day return policy",
        ),
    ).run("tx-9")

    assert approved_result.policy_result.approved is True
    assert approved_result.payment_status == "CAPTURED"
    assert rejected_result.policy_result.approved is False
    assert rejected_result.payment_status != "CAPTURED"


def test_orchestrator_is_deterministic_for_identical_inputs(
    buyer_agent,
    successful_seller_agent,
):
    orchestrator = AgentPayOrchestrator(buyer_agent, successful_seller_agent)

    first_result = orchestrator.run("tx-10")
    second_result = orchestrator.run("tx-10")

    assert first_result == second_result


def test_final_transaction_contains_purchase_request_and_accepted_offer(
    buyer_agent,
    successful_seller_agent,
):
    result = AgentPayOrchestrator(buyer_agent, successful_seller_agent).run("tx-11")

    assert result.transaction.purchase_request.buyer_id == "buyer-1"
    assert result.transaction.accepted_offer is not None
    assert result.transaction.accepted_offer.seller_id == "seller-1"
def test_budget_guard_blocks_transaction_before_payment(
    buyer_agent,
    successful_seller_agent,
):
    budget_guard = BudgetGuard(500.0)

    orchestrator = AgentPayOrchestrator(
        buyer_agent,
        successful_seller_agent,
        budget_guard=budget_guard,
    )

    result = orchestrator.run("tx-budget-blocked")

    assert result.payment_status == "failed"
    assert result.transaction.payment_status == "failed"
    assert "budget" in result.message.lower()
    assert budget_guard.spent_amount == 0.0


def test_budget_guard_records_successful_payment(
    buyer_agent,
    successful_seller_agent,
):
    budget_guard = BudgetGuard(50000.0)

    orchestrator = AgentPayOrchestrator(
        buyer_agent,
        successful_seller_agent,
        budget_guard=budget_guard,
    )

    result = orchestrator.run("tx-budget-success")

    assert result.payment_status == "CAPTURED"
    assert budget_guard.spent_amount == 800.0
    assert budget_guard.remaining_budget() == 49200.0


def test_velocity_guard_blocks_transaction_before_payment(
    buyer_agent,
    successful_seller_agent,
):
    velocity_guard = VelocityGuard(
        max_transactions=1,
        window_seconds=60,
    )

    velocity_guard.record_execution("buyer-1")

    orchestrator = AgentPayOrchestrator(
        buyer_agent,
        successful_seller_agent,
        velocity_guard=velocity_guard,
    )

    result = orchestrator.run("tx-velocity-blocked")

    assert result.payment_status == "failed"
    assert result.transaction.payment_status == "failed"
    assert "velocity" in result.message.lower()


def test_guards_allow_transaction_when_all_checks_pass(
    buyer_agent,
    successful_seller_agent,
):
    budget_guard = BudgetGuard(50000.0)
    velocity_guard = VelocityGuard(
        max_transactions=5,
        window_seconds=60,
    )

    orchestrator = AgentPayOrchestrator(
        buyer_agent,
        successful_seller_agent,
        budget_guard=budget_guard,
        velocity_guard=velocity_guard,
    )

    result = orchestrator.run("tx-guards-pass")

    assert result.payment_status == "CAPTURED"
    assert budget_guard.spent_amount == 800.0
    assert velocity_guard.current_count("buyer-1") == 1
