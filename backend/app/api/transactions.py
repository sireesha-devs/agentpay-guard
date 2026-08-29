from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.agents.buyer import BuyerAgent
from backend.app.agents.seller import SellerAgent
from backend.app.orchestration.service import AgentPayOrchestrator, TransactionResult


router = APIRouter()


class TransactionCreateRequest(BaseModel):
    """The buyer and seller constraints needed to run one transaction flow."""

    transaction_id: str = Field(default="transaction-1", min_length=1)
    buyer_id: str
    quantity: int = Field(gt=0)
    max_budget: float = Field(gt=0)
    currency: str
    minimum_refund_days: int = Field(ge=0)
    seller_id: str
    unit_price: float = Field(gt=0)
    seller_currency: str
    refund_days: int = Field(ge=0)
    terms: str
    max_rounds: int = Field(default=3, ge=1)


@router.post("/transactions", response_model=TransactionResult)
def create_transaction(request: TransactionCreateRequest) -> TransactionResult:
    """Run the existing deterministic transaction flow for the supplied constraints."""
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
