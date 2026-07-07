"""Market-data response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class Candle(BaseModel):
    time: int = Field(..., description="Unix timestamp in seconds")
    open: float
    high: float
    low: float
    close: float
    volume: float


class TradeMarker(BaseModel):
    time: int = Field(..., description="Unix timestamp in seconds")
    position: Literal["aboveBar", "belowBar"]
    color: str
    shape: Literal["arrowUp", "arrowDown"]
    text: Literal["Buy", "Sell"]


class KLineResponse(BaseModel):
    symbol: str
    candles: list[Candle]
    markers: list[TradeMarker]
