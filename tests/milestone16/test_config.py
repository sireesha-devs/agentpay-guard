import pytest

from backend.app.config import RazorpayConfig


def test_loads_valid_test_mode_configuration(monkeypatch):
    monkeypatch.setenv(
        "RAZORPAY_KEY_ID",
        "rzp_test_example",
    )
    monkeypatch.setenv(
        "RAZORPAY_KEY_SECRET",
        "test-secret",
    )

    config = RazorpayConfig.from_environment()

    assert config.key_id == "rzp_test_example"
    assert config.key_secret == "test-secret"


def test_rejects_missing_key_id(monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.setenv(
        "RAZORPAY_KEY_SECRET",
        "test-secret",
    )

    with pytest.raises(ValueError, match="credentials"):
        RazorpayConfig.from_environment()


def test_rejects_missing_secret(monkeypatch):
    monkeypatch.setenv(
        "RAZORPAY_KEY_ID",
        "rzp_test_example",
    )
    monkeypatch.delenv(
        "RAZORPAY_KEY_SECRET",
        raising=False,
    )

    with pytest.raises(ValueError, match="credentials"):
        RazorpayConfig.from_environment()


def test_rejects_live_key(monkeypatch):
    monkeypatch.setenv(
        "RAZORPAY_KEY_ID",
        "rzp_live_example",
    )
    monkeypatch.setenv(
        "RAZORPAY_KEY_SECRET",
        "live-secret",
    )

    with pytest.raises(ValueError, match="Test Mode"):
        RazorpayConfig.from_environment()


def test_strips_environment_values(monkeypatch):
    monkeypatch.setenv(
        "RAZORPAY_KEY_ID",
        "  rzp_test_example  ",
    )
    monkeypatch.setenv(
        "RAZORPAY_KEY_SECRET",
        "  test-secret  ",
    )

    config = RazorpayConfig.from_environment()

    assert config.key_id == "rzp_test_example"
    assert config.key_secret == "test-secret"