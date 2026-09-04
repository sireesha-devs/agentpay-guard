import pytest

from backend.app.payments.razorpay_gateway import RazorpayGateway


class FakeOrderAPI:
    def create(self, data):
        assert data["amount"] == 12500
        assert data["currency"] == "INR"
        assert data["receipt"] == "tx-001"

        return {
            "id": "order_test_123",
            "amount": 12500,
            "currency": "INR",
            "receipt": "tx-001",
            "status": "created",
        }


class FakeRazorpayClient:
    def __init__(self):
        self.order = FakeOrderAPI()


def test_create_order_uses_currency_subunits(monkeypatch):
    gateway = RazorpayGateway(
        key_id="rzp_test_demo",
        key_secret="test-secret",
    )

    gateway._client = FakeRazorpayClient()

    order = gateway.create_order(
        amount=125.00,
        currency="inr",
        receipt="tx-001",
    )

    assert order.order_id == "order_test_123"
    assert order.amount == 12500
    assert order.currency == "INR"
    assert order.status == "created"
    assert order.receipt == "tx-001"


def test_live_key_is_rejected():
    with pytest.raises(ValueError, match="Test Mode"):
        RazorpayGateway(
            key_id="rzp_live_demo",
            key_secret="live-secret",
        )


def test_missing_credentials_are_rejected():
    with pytest.raises(ValueError, match="credentials"):
        RazorpayGateway(
            key_id="",
            key_secret="",
        )


def test_invalid_amount_is_rejected():
    gateway = RazorpayGateway(
        key_id="rzp_test_demo",
        key_secret="test-secret",
    )

    with pytest.raises(ValueError, match="greater than zero"):
        gateway.create_order(
            amount=0,
            currency="INR",
            receipt="tx-001",
        )


def test_empty_receipt_is_rejected():
    gateway = RazorpayGateway(
        key_id="rzp_test_demo",
        key_secret="test-secret",
    )

    with pytest.raises(ValueError, match="receipt"):
        gateway.create_order(
            amount=100,
            currency="INR",
            receipt="",
        )