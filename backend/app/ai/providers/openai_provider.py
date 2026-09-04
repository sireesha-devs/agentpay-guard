from __future__ import annotations

import json
import os

from openai import OpenAI

from backend.app.ai.providers.base import (
    AIProvider,
    AIProviderRequest,
    AIProviderResponse,
)


class OpenAITransactionProvider(AIProvider):
    """
    OpenAI-backed transaction risk provider.

    The provider only recommends a decision.
    Deterministic guardrails remain the final authority.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        client: OpenAI | None = None,
    ) -> None:
        self._api_key = (
            api_key
            if api_key is not None
            else os.getenv("OPENAI_API_KEY", "").strip()
        )

        self._model = (
            model
            if model is not None
            else os.getenv("OPENAI_MODEL", "gpt-5.6-luna").strip()
        )

        if not self._api_key:
            raise ValueError("OPENAI_API_KEY is required.")

        if not self._model:
            raise ValueError("OPENAI_MODEL is required.")

        self._client = client or OpenAI(api_key=self._api_key)

    def evaluate(
        self,
        request: AIProviderRequest,
    ) -> AIProviderResponse:
        response = self._client.responses.create(
            model=self._model,
            instructions=(
                "You are a transaction risk analysis assistant. "
                "Analyze the transaction context and return ONLY valid JSON. "
                "You recommend a decision; you do not authorize payments. "
                "Never assume that your recommendation overrides deterministic "
                "security controls."
            ),
            input=self._build_input(request),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "transaction_risk_decision",
                    "description": "Structured transaction risk assessment.",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "decision": {
                                "type": "string",
                                "enum": [
                                    "APPROVE",
                                    "BLOCK",
                                    "REVIEW",
                                ],
                            },
                            "risk_score": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100,
                            },
                            "confidence": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                            "reasoning": {
                                "type": "string",
                            },
                            "risk_factors": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                },
                            },
                            "recommended_action": {
                                "type": "string",
                            },
                        },
                        "required": [
                            "decision",
                            "risk_score",
                            "confidence",
                            "reasoning",
                            "risk_factors",
                            "recommended_action",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
        )

        output = response.output_text.strip()

        if not output:
            raise ValueError("OpenAI returned an empty response.")

        data = json.loads(output)

        return AIProviderResponse(
            decision=data["decision"],
            risk_score=int(data["risk_score"]),
            confidence=float(data["confidence"]),
            reasoning=data["reasoning"],
            risk_factors=tuple(data["risk_factors"]),
            recommended_action=data["recommended_action"],
        )

    @staticmethod
    def _build_input(request: AIProviderRequest) -> str:
        return (
            "Evaluate this transaction:\n"
            f"Transaction ID: {request.transaction_id}\n"
            f"Amount: {request.amount}\n"
            f"Currency: {request.currency}\n"
            f"Merchant ID: {request.merchant_id}\n"
            f"Item category: {request.item_category}\n"
            f"Additional context: {request.context}\n"
        )