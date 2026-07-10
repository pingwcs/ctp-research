"""Domain contracts for the quant runtime boundary.

业务功能: 定义 appapi/CLI/worker 与 quant_runtime 之间传递的领域请求、成交、
权益曲线和错误包。
算法要点: 输入 payload 在边界处归一化成 dataclass，时间字符串支持 ISO/Z
格式，缺省时区按中国期货市场常用 UTC+8 处理。
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from quant_runtime.backtest_config import default_strategy_id


DEFAULT_MARKET_TIMEZONE = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class BacktestRequest:
    """业务功能: 一次回测请求的领域模型。"""

    symbol: str
    strategy: str = field(default_factory=default_strategy_id)
    start_time: datetime | None = None
    end_time: datetime | None = None
    metrics: list[str] = field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "BacktestRequest":
        """业务功能: 将 JSON payload 转换为 BacktestRequest。

        算法要点: 缺省 strategy 使用配置中的默认策略；无时区时间按
        DEFAULT_MARKET_TIMEZONE 补齐，防止和有时区时间比较时报错。
        """
        def parse_time(value: Any) -> datetime | None:
            if value in (None, ""):
                return None
            if not isinstance(value, str):
                raise ValueError("start_time and end_time must be ISO strings")
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=DEFAULT_MARKET_TIMEZONE)
            return parsed

        if "symbol" not in payload:
            raise ValueError("symbol is required")
        metrics = payload.get("metrics") or []
        if not isinstance(metrics, list) or not all(
            isinstance(item, str) for item in metrics
        ):
            raise ValueError("metrics must be a list of strings")

        return cls(
            symbol=str(payload["symbol"]),
            strategy=str(payload.get("strategy") or default_strategy_id()),
            start_time=parse_time(payload.get("start_time")),
            end_time=parse_time(payload.get("end_time")),
            metrics=metrics,
        )


@dataclass(frozen=True)
class BacktestTrade:
    """业务功能: 回测成交记录，供前端标注买卖点和成交明细。"""

    time: int
    side: Literal["buy", "sell"]
    price: float
    quantity: int
    cash: float
    reason: str


@dataclass(frozen=True)
class EquityPoint:
    """业务功能: 权益曲线采样点，表达账户权益、现金和持仓价值。"""

    time: int
    equity: float
    cash: float
    position_value: float
    position: int


@dataclass(frozen=True)
class BacktestDomainResult:
    """业务功能: quant_runtime 返回给外部调用方的完整回测领域结果。"""

    symbol: str
    strategy: str
    engine: str
    initial_cash: float
    final_equity: float
    trades: list[BacktestTrade]
    equity_curve: list[EquityPoint]
    metrics: dict[str, float | None]

    def to_jsonable(self) -> dict[str, Any]:
        """业务功能: 转换为可 JSON 序列化的字典。"""
        return asdict(self)


@dataclass(frozen=True)
class RunnerError(Exception):
    """业务功能: 运行时可控错误，携带 HTTP 友好的状态码和说明。"""

    status_code: int
    detail: str

    def to_jsonable(self) -> dict[str, Any]:
        """业务功能: 转换为 runner/worker 协议的错误 JSON。"""
        return {"error": {"status_code": self.status_code, "detail": self.detail}}
