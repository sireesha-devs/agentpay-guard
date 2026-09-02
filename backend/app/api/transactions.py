from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.agents.buyer import BuyerAgent
from backend.app.agents.seller import SellerAgent
from backend.app.orchestration.service import AgentPayOrchestrator, TransactionResult
from backend.app.security.auth import authenticate


router = APIRouter()


class TransactionCreateRequest(BaseModel):
    """Strict request model for a transaction."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    transaction_id: str = Field(
        default="transaction-1",
        min_length=1,
        max_length=100,
    )
    buyer_id: str = Field(
        min_length=1,
        max_length=100,
    )
    quantity: int = Field(
        gt=0,
        le=1_000_000,
    )
    max_budget: float = Field(
        gt=0,
        le=1_000_000_000,
    )
    currency: str = Field(
        min_length=3,
        max_length=3,
    )
    minimum_refund_days: int = Field(
        ge=0,
        le=3650,
    )
    seller_id: str = Field(
        min_length=1,
        max_length=100,
    )
    unit_price: float = Field(
        gt=0,
        le=1_000_000_000,
    )
    seller_currency: str = Field(
        min_length=3,
        max_length=3,
    )
    refund_days: int = Field(
        ge=0,
        le=3650,
    )
    terms: str = Field(
        min_length=1,
        max_length=5000,
    )
    max_rounds: int = Field(
        default=3,
        ge=1,
        le=20,
    )

    @field_validator("currency", "seller_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        value = value.upper()

        if not value.isalpha():
            raise ValueError("Currency must contain only letters")

        return value

    @field_validator("max_budget", "unit_price")
    @classmethod
    def validate_finite_amount(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Amount must be finite")
        return value

    @field_validator(
        "transaction_id",
        "buyer_id",
        "seller_id",
        "terms",
    )
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value cannot be blank")
        return value


def buyer_or_admin(
    x_api_key: str | None = Header(
        default=None,
        alias="X-API-Key",
    ),
) -> str:
    """Allow buyer and admin API keys to access transactions."""
    return authenticate(x_api_key, required_role="buyer")


@router.post(
    "/transactions",
    response_model=TransactionResult,
    summary="Run a deterministic transaction",
    description=(
        "Creates buyer and seller agents and delegates the transaction flow "
        "to the existing deterministic orchestrator."
    ),
    responses={
        401: {"description": "Missing or invalid API key."},
        403: {"description": "Insufficient role permissions."},
        422: {"description": "Request validation failed."},
        429: {"description": "Rate limit exceeded."},
    },
)
def create_transaction(
    request: TransactionCreateRequest,
    role: str = Depends(buyer_or_admin),
) -> TransactionResult:
    """Run the existing deterministic transaction flow."""
    buyer_agent = BuyerAgent(
        buyer_id=request.buyer_id,
        quantity=request.quantity,
        max_budget=request.max_budget,
        currency=request.currency,
        minimum_refund_days=request.minimum_refund_days,
    )

    seller_agent = SellerAgent(
        seller_id=request.seller_id,
        unit_price=request.unit_price,
        refund_days=request.refund_days,
        currency=request.seller_currency,
        terms=request.terms,
    )

    orchestrator = AgentPayOrchestrator(
        buyer_agent,
        seller_agent,
        max_rounds=request.max_rounds,
    )

    return orchestrator.run(request.transaction_id)
