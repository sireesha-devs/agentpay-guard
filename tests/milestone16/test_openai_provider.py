import json

import pytest

from backend.app.ai.providers.base import AIProviderRequest
from backend.app.ai.providers.openai_provider import OpenAITransactionProvider


REQUEST = AIProviderRequest(
    transaction_id="tx-openai-1",
    amount=1500.0,
    currency="INR",
    merchant_id="merchant-1",
    item_category="electronics",
    context="Normal customer purchase",
)


class FakeResponse:
    def __init__(self, output: dict) -> None:
        self.output_text = json.dumps(output)


class FakeResponses:
    def __init__(self, output: dict) -> None:
        self._output = output
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return FakeResponse(self._output)


class FakeClient:
    def __init__(self, output: dict) -> None:
        self.responses = FakeResponses(output)


def valid_output() -> dict:
    return {
        "decision": "APPROVE",
        "risk_score": 12,
        "confidence": 0.96,
        "reasoning": "Transaction context appears normal.",
        "risk_factors": ["NORMAL_TRANSACTION"],
        "recommended_action": "PROCEED_WITH_PAYMENT",
    }


def test_openai_provider_returns_structured_decision():
    provider = OpenAITransactionProvider(
        api_key="test-key",
        model="test-model",
        client=FakeClient(valid_output()),
    )

    result = provider.evaluate(REQUEST)

    assert result.decision == "APPROVE"
    assert result.risk_score == 12
    assert result.confidence == 0.96
    assert result.risk_factors == ("NORMAL_TRANSACTION",)
    assert result.recommended_action == "PROCEED_WITH_PAYMENT"


def test_openai_provider_sends_transaction_context():
    client = FakeClient(valid_output())

    provider = OpenAITransactionProvider(
        api_key="test-key",
        model="test-model",
        client=client,
    )

    provider.evaluate(REQUEST)

    kwargs = client.responses.last_kwargs

    assert kwargs["model"] == "test-model"
    assert "tx-openai-1" in kwargs["input"]
    assert "1500.0" in kwargs["input"]
    assert "INR" in kwargs["input"]
    assert "merchant-1" in kwargs["input"]
    assert "electronics" in kwargs["input"]


def test_openai_provider_requests_strict_structured_output():
    client = FakeClient(valid_output())

    provider = OpenAITransactionProvider(
        api_key="test-key",
        model="test-model",
        client=client,
    )

    provider.evaluate(REQUEST)

    format_config = client.responses.last_kwargs["text"]["format"]

    assert format_config["type"] == "json_schema"
    assert format_config["strict"] is True
    assert format_config["name"] == "transaction_risk_decision"


def test_missing_api_key_is_rejected():
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAITransactionProvider(
            api_key="",
            model="test-model",
        )


def test_missing_model_is_rejected():
    with pytest.raises(ValueError, match="OPENAI_MODEL"):
        OpenAITransactionProvider(
            api_key="test-key",
            model="",
        )


def test_empty_model_response_is_rejected():
    class EmptyClient:
        class responses:
            @staticmethod
            def create(**kwargs):
                return FakeResponse({})

        responses = responses()

    provider = OpenAITransactionProvider(
        api_key="test-key",
        model="test-model",
        client=EmptyClient(),
    )

    EmptyClient.responses.create = lambda **kwargs: type(
        "Response",
        (),
        {"output_text": ""},
    )()

    with pytest.raises(ValueError, match="empty response"):
        provider.evaluate(REQUEST)