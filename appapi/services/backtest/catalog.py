"""Backtest metadata and symbol discovery."""

from appapi.core.config import settings
from appapi.schemas.backtest import MetricInfo, StrategyInfo


STRATEGIES = [
    StrategyInfo(
        id="ma_cross",
        name="MA5/MA20 Cross",
        description=(
            "Buy on MA5 crossing above MA20, "
            "sell on MA5 crossing below MA20."
        ),
    ),
]

METRICS = [
    MetricInfo(
        id="total_return",
        name="Total Return",
        description="Total equity return.",
    ),
    MetricInfo(
        id="annual_return",
        name="Annual Return",
        description="Annualized return.",
    ),
    MetricInfo(
        id="sharpe",
        name="Sharpe Ratio",
        description="Annualized Sharpe ratio.",
    ),
    MetricInfo(
        id="max_drawdown",
        name="Max Drawdown",
        description="Largest equity drawdown.",
    ),
    MetricInfo(
        id="win_rate",
        name="Win Rate",
        description="Winning sell trades ratio.",
    ),
]


def available_metric_ids() -> set[str]:
    return {metric.id for metric in METRICS}


def list_backtest_symbols() -> list[str]:
    data_dir = settings.data_dir.resolve()
    if not data_dir.exists():
        return []
    return sorted(
        path.stem
        for path in data_dir.glob("RB*.parquet")
        if path.is_file()
    )
