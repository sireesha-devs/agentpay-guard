import pytest

from backend.app.models.transaction import Offer, PolicyResult, PurchaseRequest, Transaction
from backend.app.payments.service import PaymentService, PaymentStatus


@pytest.fixture
def purchase_request() -> PurchaseRequest:
    return PurchaseRequest(
        buyer_id="buyer-1",
        quantity=2,
        max_budget=1000.0,
        currency="INR",
        minimum_refund_days=7,
    )


@pytest.fixture
def accepted_offer() -> Offer:
    return Offer(
        seller_id="seller-1",
        quantity=2,
        unit_price=400.0,
        currency="INR",
        refund_days=7,
        terms="Seven-day return policy",
    )


@pytest.fixture
def approved_transaction(purchase_request, accepted_offer) -> Transaction:
    return Transaction(
        transaction_id="transaction-1",
        purchase_request=purchase_request,
        accepted_offer=accepted_offer,
        policy_result=PolicyResult(
            approved=True,
            reason="Offer passed all policy checks.",
            violations=[],
        ),
        payment_status="pending",
    )


def test_approved_transaction_with_offer_is_captured(approved_transaction):
    result = PaymentService().capture_payment(approved_transaction)

    assert result.status == PaymentStatus.CAPTURED


def test_captured_amount_equals_quantity_times_unit_price(approved_transaction):
    result = PaymentService().capture_payment(approved_transaction)

    assert result.amount == 800.0


def test_captured_currency_equals_accepted_offer_currency(approved_transaction):
    result = PaymentService().capture_payment(approved_transaction)

    assert result.currency == "INR"


def test_policy_rejected_transaction_results_in_failed_payment(
    purchase_request,
    accepted_offer,
):
    transaction = Transaction(
        transaction_id="transaction-2",
        purchase_request=purchase_request,
        accepted_offer=accepted_offer,
        policy_result=PolicyResult(
            approved=False,
            reason="Budget exceeded.",
            violations=["Offer total cost exceeds maximum budget."],
        ),
        payment_status="pending",
    )

    result = PaymentService().capture_payment(transaction)

    assert result.status == PaymentStatus.FAILED


def test_transaction_without_policy_result_results_in_failed_payment(
    purchase_request,
    accepted_offer,
):
    transaction = Transaction(
        transaction_id="transaction-3",
        purchase_request=purchase_request,
        accepted_offer=accepted_offer,
        payment_status="pending",
    )

    result = PaymentService().capture_payment(transaction)

    assert result.status == PaymentStatus.FAILED


def test_transaction_without_accepted_offer_results_in_failed_payment(purchase_request):
    transaction = Transaction(
        transaction_id="transaction-4",
        purchase_request=purchase_request,
        policy_result=PolicyResult(
            approved=True,
            reason="Offer passed all policy checks.",
            violations=[],
        ),
        payment_status="pending",
    )

    result = PaymentService().capture_payment(transaction)

    assert result.status == PaymentStatus.FAILED


def test_payment_result_contains_transaction_id(approved_transaction):
    result = PaymentService().capture_payment(approved_transaction)

    assert result.transaction_id == "transaction-1"


def test_payment_service_is_deterministic_for_same_transaction(approved_transaction):
    service = PaymentService()

    first_result = service.capture_payment(approved_transaction)
    second_result = service.capture_payment(approved_transaction)

    assert first_result == second_result
