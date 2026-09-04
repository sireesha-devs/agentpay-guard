from datetime import datetime, timezone

from backend.app.ai.decision import AIDecision
from backend.app.guards.pipeline import (
    GuardCheckResult,
    GuardPipelineResult,
)
from backend.app.payments.guarded_executor import (
    GuardedRazorpayExecutor,
)
from backend.app.payments.razorpay_gateway import (
    RazorpayOrder,
)


class FakeGateway:
    def __init__(self):
        self.calls = []

    def create_order(self, amount, currency, receipt):
        self.calls.append(
            {
                "amount": amount,
                "currency": currency,
                "receipt": receipt,
            }
        )

        return RazorpayOrder(
            order_id="order_test_001",
            amount=int(amount * 100),
            currency=currency,
            status="created",
            receipt=receipt,
        )


def make_guard_result(allowed=True):
    return GuardPipelineResult(
        allowed=allowed,
        final_disposition="ALLOWED" if allowed else "BLOCKED",
        checks=(
            GuardCheckResult(
                guard_name="budget",
                passed=allowed,
                reason_code=(
                    "BUDGET_OK"
                    if allowed
                    else "BUDGET_EXCEEDED"
                ),
                message="Budget check",
            ),
        ),
        timestamp_utc=datetime.now(timezone.utc),
    )


def approve_decision():
    return AIDecision(
        decision="APPROVE",
        risk_score=10,
        confidence=0.99,
        reasoning="All deterministic guards passed.",
        risk_factors=[],
        recommended_action="PROCEED_WITH_PAYMENT",
    )


def block_decision():
    return AIDecision(
        decision="BLOCK",
        risk_score=90,
        confidence=0.99,
        reasoning="Transaction blocked.",
        risk_factors=["BUDGET_EXCEEDED"],
        recommended_action="REJECT_TRANSACTION",
    )


def test_approved_transaction_creates_razorpay_order():
    gateway = FakeGateway()
    executor = GuardedRazorpayExecutor(gateway)

    result = executor.execute(
        ai_decision=approve_decision(),
        guard_result=make_guard_result(True),
        amount=125.00,
        currency="INR",
        receipt="tx-001",
    )

    assert result.allowed is True
    assert result.order is not None
    assert result.order.order_id == "order_test_001"
    assert result.order.amount == 12500
    assert result.order.currency == "INR"

    assert len(gateway.calls) == 1
    assert gateway.calls[0]["amount"] == 125.00


def test_deterministic_block_prevents_razorpay_call():
    gateway = FakeGateway()
    executor = GuardedRazorpayExecutor(gateway)

    result = executor.execute(
        ai_decision=approve_decision(),
        guard_result=make_guard_result(False),
        amount=125.00,
        currency="INR",
        receipt="tx-002",
    )

    assert result.allowed is False
    assert result.order is None
    assert len(gateway.calls) == 0
    assert "deterministic" in result.reason.lower()


def test_ai_block_prevents_razorpay_call():
    gateway = FakeGateway()
    executor = GuardedRazorpayExecutor(gateway)

    result = executor.execute(
        ai_decision=block_decision(),
        guard_result=make_guard_result(True),
        amount=125.00,
        currency="INR",
        receipt="tx-003",
    )

    assert result.allowed is False
    assert result.order is None
    assert len(gateway.calls) == 0
    assert "AI" in result.reason


def test_deterministic_guard_overrides_ai_approval():
    gateway = FakeGateway()
    executor = GuardedRazorpayExecutor(gateway)

    result = executor.execute(
        ai_decision=approve_decision(),
        guard_result=make_guard_result(False),
        amount=50000.00,
        currency="INR",
        receipt="tx-004",
    )

    assert result.allowed is False
    assert result.ai_decision == "APPROVE"
    assert result.deterministic_disposition == "BLOCKED"
    assert result.order is None
    assert gateway.calls == []