from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AIProviderRequest:
    transaction_id: str
    amount: float
    currency: str
    merchant_id: str
    item_category: str
    context: str


@dataclass(frozen=True)
class AIProviderResponse:
    decision: str
    risk_score: int
    confidence: float
    reasoning: str
    risk_factors: tuple[str, ...]
    recommended_action: str


class AIProvider(ABC):
    """Provider contract for AgentPay Guard's AI decision layer."""

    @abstractmethod
    def evaluate(self, request: AIProviderRequest) -> AIProviderResponse:
        """Evaluate a transaction using an AI provider."""
        raise NotImplementedError