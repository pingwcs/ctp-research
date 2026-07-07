"""Backtest request and response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class StrategyInfo(BaseModel):
    id: str
    name: str
    description: str


class MetricInfo(BaseModel):
    id: str
    name: str
    description: str


class BacktestRunRequest(BaseModel):
    symbol: str = Field(..., examples=["RB0909"])
    strategy: str = Field(default="ma_cross")
    start_time: datetime | None = None
    end_time: datetime | None = None
    metrics: list[str] = Field(default_factory=list)


class BacktestTrade(BaseModel):
    time: int
    side: Literal["buy", "sell"]
    price: float
    quantity: int
    cash: float
    reason: str


class EquityPoint(BaseModel):
    time: int
    equity: float
    cash: float
    position_value: float
    position: int


class BacktestRunResponse(BaseModel):
    symbol: str
    strategy: str
    initial_cash: float
    final_equity: float
    trades: list[BacktestTrade]
    equity_curve: list[EquityPoint]
    metrics: dict[str, float | None]
