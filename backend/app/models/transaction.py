from typing import Optional

from pydantic import BaseModel, Field


class PurchaseRequest(BaseModel):
    """The buyer's requested purchase constraints."""

    buyer_id: str
    quantity: int = Field(gt=0)
    max_budget: float = Field(gt=0)
    currency: str
    minimum_refund_days: int = Field(ge=0)


class Offer(BaseModel):
    """A seller's proposed terms for fulfilling a purchase request."""

    seller_id: str
    quantity: int = Field(gt=0)
    unit_price: float = Field(gt=0)
    currency: str
    refund_days: int = Field(ge=0)
    terms: str


class PolicyResult(BaseModel):
    """The outcome of evaluating a transaction against policy."""

    approved: bool
    reason: str
    violations: list[str]


class Transaction(BaseModel):
    """The purchase, offer, policy outcome, and payment state for a transaction."""

    transaction_id: str
    purchase_request: PurchaseRequest
    accepted_offer: Optional[Offer] = None
    policy_result: Optional[PolicyResult] = None
    payment_status: str
