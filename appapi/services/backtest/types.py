"""Internal backtest data structures."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestBar:
    time: int
    close: float
    ma5: float
    ma20: float
