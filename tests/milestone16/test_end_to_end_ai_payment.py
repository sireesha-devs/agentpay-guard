from datetime import datetime, timezone

from backend.app.ai.decision import AIDecision
from backend.app.ai.guarded_decision import GuardedAIDecisionService
from backend.app.ai.providers.base import AIProvider, AIProviderRequest, AIProviderResponse
from backend.app.ai.service import AIDecisionService
from backend.app.guards.pipeline import GuardPipelineResult
from backend.app.audit.models import AuditRecord, ExecutionState
from backend.app.audit.recorder import AuditRecorder
from backend.app.audit.store import AuditStore
from backend.app.guards.guardrail import GuardrailEngine
from backend.app.payments.guarded_executor import GuardedRazorpayExecutor
from backend.app.payments.razorpay_gateway import RazorpayOrder


class FakeAIProvider(AIProvider):
    def __init__(self, decision: str = "APPROVE") -> None:
        self.decision = decision

    def evaluate(self, request: AIProviderRequest) -> AIProviderResponse:
        return AIProviderResponse(
            decision=self.decision,
            risk_score=10 if self.decision == "APPROVE" else 95,
            confidence=0.99,
            reasoning="Test AI decision.",
            risk_factors=(),
            recommended_action=(
                "PROCEED_WITH_PAYMENT"
                if self.decision == "APPROVE"
                else "REJECT_TRANSACTION"
            ),
        )


class FakeRazorpayGateway:
    def __init__(self) -> None:
        self.calls = []

    def create_order(self, amount: float, currency: str, receipt: str) -> RazorpayOrder:
        self.calls.append(
            {
                "amount": amount,
                "currency": currency,
                "receipt": receipt,
            }
        )

        return RazorpayOrder(
            order_id="order_test_123",
            amount=int(amount * 100),
            currency=currency,
            status="created",
            receipt=receipt,
        )


def passing_guard_result() -> GuardPipelineResult:
    return GuardPipelineResult(
        allowed=True,
        final_disposition="ALLOWED",
        checks=[],
        timestamp_utc=datetime.now(timezone.utc),
    )


def blocked_guard_result() -> GuardPipelineResult:
    return GuardPipelineResult(
        allowed=False,
        final_disposition="BLOCKED",
        checks=[],
        timestamp_utc=datetime.now(timezone.utc),
    )


def build_ai_service(decision: str = "APPROVE") -> AIDecisionService:
    return AIDecisionService(FakeAIProvider(decision))


def test_ai_approve_and_guards_pass_create_razorpay_order() -> None:
    ai_service = build_ai_service("APPROVE")

    guarded_ai = GuardedAIDecisionService(ai_service)

    guarded_decision = guarded_ai.evaluate(
        transaction_id="txn-001",
        amount=1000.0,
        currency="INR",
        merchant_id="merchant-001",
        item_category="electronics",
        context="Normal purchase",
        guard_result=passing_guard_result(),
    )

    gateway = FakeRazorpayGateway()
    executor = GuardedRazorpayExecutor(gateway)

    result = executor.execute(
        ai_decision=guarded_decision.ai_decision,
        guard_result=passing_guard_result(),
        amount=1000.0,
        currency="INR",
        receipt="txn-001",
    )

    assert guarded_decision.allowed is True
    assert result.allowed is True
    assert result.order is not None
    assert result.order.order_id == "order_test_123"
    assert len(gateway.calls) == 1


def test_ai_approve_but_guard_blocks_never_calls_razorpay() -> None:
    ai_service = build_ai_service("APPROVE")

    guarded_ai = GuardedAIDecisionService(ai_service)

    guarded_decision = guarded_ai.evaluate(
        transaction_id="txn-002",
        amount=50000.0,
        currency="INR",
        merchant_id="merchant-001",
        item_category="electronics",
        context="High-risk transaction",
        guard_result=blocked_guard_result(),
    )

    gateway = FakeRazorpayGateway()
    executor = GuardedRazorpayExecutor(gateway)

    result = executor.execute(
        ai_decision=guarded_decision.ai_decision,
        guard_result=blocked_guard_result(),
        amount=50000.0,
        currency="INR",
        receipt="txn-002",
    )

    assert guarded_decision.allowed is False
    assert result.allowed is False
    assert result.order is None
    assert len(gateway.calls) == 0


def test_ai_block_never_calls_razorpay() -> None:
    ai_service = build_ai_service("BLOCK")

    guarded_ai = GuardedAIDecisionService(ai_service)

    guarded_decision = guarded_ai.evaluate(
        transaction_id="txn-003",
        amount=1000.0,
        currency="INR",
        merchant_id="merchant-001",
        item_category="electronics",
        context="Suspicious transaction",
        guard_result=passing_guard_result(),
    )

    gateway = FakeRazorpayGateway()
    executor = GuardedRazorpayExecutor(gateway)

    result = executor.execute(
        ai_decision=guarded_decision.ai_decision,
        guard_result=passing_guard_result(),
        amount=1000.0,
        currency="INR",
        receipt="txn-003",
    )

    assert guarded_decision.ai_decision.decision == "BLOCK"
    assert result.allowed is False
    assert result.order is None
    assert len(gateway.calls) == 0
class FailingAIProvider(AIProvider):
    def evaluate(self, request: AIProviderRequest) -> AIProviderResponse:
        raise RuntimeError("Simulated AI provider failure")


def test_ai_provider_failure_safe_blocks_and_never_calls_razorpay() -> None:
    ai_service = AIDecisionService(FailingAIProvider())

    guarded_ai = GuardedAIDecisionService(ai_service)

    guard_result = passing_guard_result()

    guarded_decision = guarded_ai.evaluate(
        transaction_id="txn-004",
        amount=1000.0,
        currency="INR",
        merchant_id="merchant-001",
        item_category="electronics",
        context="Provider failure test",
        guard_result=guard_result,
    )

    gateway = FakeRazorpayGateway()
    executor = GuardedRazorpayExecutor(gateway)

    result = executor.execute(
        ai_decision=guarded_decision.ai_decision,
        guard_result=guard_result,
        amount=1000.0,
        currency="INR",
        receipt="txn-004",
    )

    assert guarded_decision.ai_decision.decision == "BLOCK"
    assert guarded_decision.ai_decision.risk_score == 100
    assert guarded_decision.allowed is False

    assert result.allowed is False
    assert result.order is None
    assert len(gateway.calls) == 0
def test_successful_ai_payment_creates_auditable_event(tmp_path) -> None:
    store = AuditStore(tmp_path / "audit.jsonl")
    recorder = AuditRecorder(store=store)

    ai_service = build_ai_service("APPROVE")
    guarded_ai = GuardedAIDecisionService(ai_service)

    guard_result = passing_guard_result()

    guarded_decision = guarded_ai.evaluate(
        transaction_id="txn-005",
        amount=1000.0,
        currency="INR",
        merchant_id="merchant-001",
        item_category="electronics",
        context="Normal purchase",
        guard_result=guard_result,
    )

    gateway = FakeRazorpayGateway()
    executor = GuardedRazorpayExecutor(gateway)

    result = executor.execute(
        ai_decision=guarded_decision.ai_decision,
        guard_result=guard_result,
        amount=1000.0,
        currency="INR",
        receipt="txn-005",
    )

    assert result.allowed is True
    assert result.order is not None

    audit_event = recorder.record(
        AuditRecord(
            transaction_id="txn-005",
            agent_id="commerce-agent",
            model_version="m16.9-test",
            prompt_hash="test-prompt-hash",
            session_id="session-005",
            timestamp_utc=datetime.now(timezone.utc),
            requested_amount=1000.0,
            currency="INR",
            payment_method="razorpay",
            gateway_order_id=result.order.order_id,
            signature_valid=None,
            execution_state=ExecutionState.CAPTURED,
            gateway_response_code=result.order.status,
            failure_message=None,
        )
    )

    assert audit_event.gateway_order_id == "order_test_123"
    assert audit_event.execution_state == ExecutionState.CAPTURED
    assert audit_event.event_hash is not None
    assert audit_event.previous_event_hash is None

    assert recorder.verify_chain() is True
    assert recorder.verify_persisted_chain() is True
    assert store.count() == 1
def test_blocked_payment_creates_audit_event_without_gateway_order(
    tmp_path,
) -> None:
    store = AuditStore(tmp_path / "audit.jsonl")
    recorder = AuditRecorder(store=store)

    ai_service = build_ai_service("APPROVE")
    guarded_ai = GuardedAIDecisionService(ai_service)

    guard_result = blocked_guard_result()

    guarded_decision = guarded_ai.evaluate(
        transaction_id="txn-006",
        amount=50000.0,
        currency="INR",
        merchant_id="merchant-001",
        item_category="electronics",
        context="Guard block test",
        guard_result=guard_result,
    )

    gateway = FakeRazorpayGateway()
    executor = GuardedRazorpayExecutor(gateway)

    result = executor.execute(
        ai_decision=guarded_decision.ai_decision,
        guard_result=guard_result,
        amount=50000.0,
        currency="INR",
        receipt="txn-006",
    )

    assert result.allowed is False
    assert result.order is None
    assert len(gateway.calls) == 0

    audit_event = recorder.record(
        AuditRecord(
            transaction_id="txn-006",
            agent_id="commerce-agent",
            model_version="m16.9-test",
            prompt_hash="test-prompt-hash",
            session_id="session-006",
            timestamp_utc=datetime.now(timezone.utc),
            requested_amount=50000.0,
            currency="INR",
            payment_method="razorpay",
            gateway_order_id=None,
            signature_valid=None,
            execution_state=ExecutionState.BLOCKED,
            gateway_response_code=None,
            failure_message=result.reason,
        )
    )

    assert audit_event.execution_state == ExecutionState.BLOCKED
    assert audit_event.gateway_order_id is None
    assert audit_event.failure_message is not None
    assert "deterministic" in audit_event.failure_message.lower()

    assert recorder.verify_chain() is True
    assert recorder.verify_persisted_chain() is True
    assert store.count() == 1

def test_ai_failure_creates_blocked_audit_event_without_gateway_order(
    tmp_path,
) -> None:
    store = AuditStore(tmp_path / "audit.jsonl")
    recorder = AuditRecorder(store=store)

    ai_service = AIDecisionService(FailingAIProvider())
    guarded_ai = GuardedAIDecisionService(ai_service)

    guard_result = passing_guard_result()

    guarded_decision = guarded_ai.evaluate(
        transaction_id="txn-007",
        amount=1000.0,
        currency="INR",
        merchant_id="merchant-001",
        item_category="electronics",
        context="AI provider failure test",
        guard_result=guard_result,
    )

    gateway = FakeRazorpayGateway()
    executor = GuardedRazorpayExecutor(gateway)

    result = executor.execute(
        ai_decision=guarded_decision.ai_decision,
        guard_result=guard_result,
        amount=1000.0,
        currency="INR",
        receipt="txn-007",
    )

    assert guarded_decision.ai_decision.decision == "BLOCK"
    assert guarded_decision.ai_decision.risk_score == 100
    assert guarded_decision.allowed is False

    assert result.allowed is False
    assert result.order is None
    assert len(gateway.calls) == 0

    audit_event = recorder.record(
        AuditRecord(
            transaction_id="txn-007",
            agent_id="commerce-agent",
            model_version="m16.9-test",
            prompt_hash="test-prompt-hash",
            session_id="session-007",
            timestamp_utc=datetime.now(timezone.utc),
            requested_amount=1000.0,
            currency="INR",
            payment_method="razorpay",
            gateway_order_id=None,
            signature_valid=None,
            execution_state=ExecutionState.BLOCKED,
            gateway_response_code=None,
            failure_message=guarded_decision.ai_decision.reasoning,
            injection_detected=None,
            injection_risk_score=None,
        )
    )

    assert audit_event.execution_state == ExecutionState.BLOCKED
    assert audit_event.gateway_order_id is None
    assert "unavailable" in audit_event.failure_message.lower()

    assert recorder.verify_chain() is True
    assert recorder.verify_persisted_chain() is True
    assert store.count() == 1