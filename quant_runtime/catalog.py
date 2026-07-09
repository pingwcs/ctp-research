"""Strategy and metric metadata owned by the quant runtime."""

from pathlib import Path
import re

from quant_runtime.backtest_config import (
    EngineConfig,
    MetricConfig,
    StrategyConfig,
    clear_backtest_config_cache,
    load_backtest_config,
)
from quant_runtime.contracts import RunnerError


SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def metadata() -> dict[str, list[dict[str, str]]]:
    config = load_backtest_config()
    return {
        "strategies": [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "engine": item.engine,
            }
            for item in config.strategies
        ],
        "metrics": [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
            }
            for item in config.metrics
        ],
    }


def metric_ids() -> set[str]:
    return {metric.id for metric in load_backtest_config().metrics}


def strategy_ids() -> set[str]:
    return {strategy.id for strategy in load_backtest_config().strategies}


def clear_catalog_cache() -> None:
    clear_backtest_config_cache()


def engine_config() -> EngineConfig:
    return load_backtest_config().engine


def metric_config(metric_id: str) -> MetricConfig:
    return load_backtest_config().metric(metric_id)


def strategy_config(strategy_id: str) -> StrategyConfig:
    return load_backtest_config().strategy(strategy_id)


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
