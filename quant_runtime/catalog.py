"""Strategy and metric metadata owned by the quant runtime."""

from dataclasses import asdict, dataclass
from pathlib import Path
import re

from quant_runtime.contracts import RunnerError


SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class StrategyInfo:
    id: str
    name: str
    description: str
    engine: str


@dataclass(frozen=True)
class MetricInfo:
    id: str
    name: str
    description: str


STRATEGIES = [
    StrategyInfo(
        id="ma_cross",
        name="MA Cross",
        description="Moving-average cross strategy executed by the configured adapter.",
        engine="vnpy",
    ),
]

METRICS = [
    MetricInfo("total_return", "Total Return", "Total equity return."),
    MetricInfo("annual_return", "Annual Return", "Annualized return."),
    MetricInfo("sharpe", "Sharpe Ratio", "Annualized Sharpe ratio."),
    MetricInfo("max_drawdown", "Max Drawdown", "Largest equity drawdown."),
    MetricInfo("win_rate", "Win Rate", "Winning closed-trade ratio."),
]


def metadata() -> dict[str, list[dict[str, str]]]:
    return {
        "strategies": [asdict(item) for item in STRATEGIES],
        "metrics": [asdict(item) for item in METRICS],
    }


def metric_ids() -> set[str]:
    return {metric.id for metric in METRICS}


def strategy_ids() -> set[str]:
    return {strategy.id for strategy in STRATEGIES}


def validate_symbol(symbol: str) -> None:
    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise RunnerError(
            400,
            "symbol may only contain letters, numbers, underscore, dash and dot",
        )


def validate_request_ids(strategy: str, metrics: list[str]) -> list[str]:
    if strategy not in strategy_ids():
        raise RunnerError(400, f"unsupported strategy: {strategy}")

    selected = metrics or sorted(metric_ids())
    invalid = [metric for metric in selected if metric not in metric_ids()]
    if invalid:
        raise RunnerError(400, f"unsupported metrics: {', '.join(invalid)}")
    return selected


def symbol_parquet_path(symbol: str, data_dir: Path) -> Path:
    validate_symbol(symbol)
    root = data_dir.resolve()
    path = (root / f"{symbol}.parquet").resolve()
    if root not in path.parents:
        raise RunnerError(400, "invalid symbol path")
    if not path.exists():
        raise RunnerError(404, f"contract parquet not found: {path}")
    return path
