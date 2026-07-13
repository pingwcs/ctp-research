"""Request and response contracts for manual futures limit orders."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CreateOrderCommandRequest(BaseModel):
    """One manual GFD limit-order intent accepted by the HTTP boundary."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1, max_length=64)
    exchange: str = Field(min_length=1, max_length=16)
    direction: Literal["LONG", "SHORT"]
    offset_policy: Literal["OPEN", "CLOSE_AUTO"]
    limit_price: Decimal = Field(gt=Decimal("0"), max_digits=20, decimal_places=8)
    volume: int = Field(gt=0, le=1_000_000)


class OrderCommandResponse(BaseModel):
    """Durable command acknowledgement, not a broker acceptance response."""

    command_id: str
    order_intent_id: str
    status: Literal["PENDING"]
