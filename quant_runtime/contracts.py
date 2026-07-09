"""Domain contracts for the quant runtime boundary."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal


DEFAULT_MARKET_TIMEZONE = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class BacktestRequest:
    symbol: str
    strategy: str = "ma_cross"
    start_time: datetime | None = None
    end_time: datetime | None = None
    metrics: list[str] = field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "BacktestRequest":
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
            strategy=str(payload.get("strategy") or "ma_cross"),
            start_time=parse_time(payload.get("start_time")),
            end_time=parse_time(payload.get("end_time")),
            metrics=metrics,
        )


@dataclass(frozen=True)
class BacktestTrade:
    time: int
    side: Literal["buy", "sell"]
    price: float
    quantity: int
    cash: float
    reason: str


@dataclass(frozen=True)
class EquityPoint:
    time: int
    equity: float
    cash: float
    position_value: float
    position: int


@dataclass(frozen=True)
class BacktestDomainResult:
    symbol: str
    strategy: str
    engine: str
    initial_cash: float
    final_equity: float
    trades: list[BacktestTrade]
    equity_curve: list[EquityPoint]
    metrics: dict[str, float | None]

    def to_jsonable(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunnerError(Exception):
    status_code: int
    detail: str

    def to_jsonable(self) -> dict[str, Any]:
        return {"error": {"status_code": self.status_code, "detail": self.detail}}
