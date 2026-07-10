"""Backtest request and response schemas.

业务功能: 定义前端与 appapi 之间的回测 HTTP 合约。
算法要点: schema 只表达传输结构和基础类型约束，策略校验、指标计算和时间
范围推断都留给 quant_runtime。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class StrategyInfo(BaseModel):
    """业务功能: 描述一个可展示、可选择的回测策略。"""

    id: str
    name: str
    description: str


class MetricInfo(BaseModel):
    """业务功能: 描述一个可展示、可选择的绩效指标。"""

    id: str
    name: str
    description: str


class BacktestRunRequest(BaseModel):
    """业务功能: 前端发起同步或异步回测时提交的请求。"""

    symbol: str = Field(..., examples=["RB0909"])
    strategy: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    metrics: list[str] = Field(default_factory=list)


class BacktestTrade(BaseModel):
    """业务功能: 回测成交明细，用于前端展示买卖点。"""

    time: int
    side: Literal["buy", "sell"]
    price: float
    quantity: int
    cash: float
    reason: str


class EquityPoint(BaseModel):
    """业务功能: 单个权益曲线点，用于展示资产、现金和持仓价值变化。"""

    time: int
    equity: float
    cash: float
    position_value: float
    position: int


class BacktestRunResponse(BaseModel):
    """业务功能: 一次回测完成后的完整前端响应。"""

    symbol: str
    strategy: str
    initial_cash: float
    final_equity: float
    trades: list[BacktestTrade]
    equity_curve: list[EquityPoint]
    metrics: dict[str, float | None]


class BacktestJobSubmitResponse(BaseModel):
    """业务功能: 异步回测提交后的任务句柄。"""

    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"]


class BacktestJobStatusResponse(BaseModel):
    """业务功能: 异步回测任务状态查询响应。"""

    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    error: str | None = None
