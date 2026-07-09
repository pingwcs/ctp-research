"""Backtest metadata and symbol discovery via quant runtime runner."""

from appapi.schemas.backtest import MetricInfo, StrategyInfo
from appapi.services.backtest.metadata_cache import runtime_metadata
from appapi.services.backtest.runner_client import invoke_runner


def get_strategies() -> list[StrategyInfo]:
    payload = runtime_metadata()
    return [StrategyInfo.model_validate(item) for item in payload.get("strategies", [])]


def get_metrics() -> list[MetricInfo]:
    payload = runtime_metadata()
    return [MetricInfo.model_validate(item) for item in payload.get("metrics", [])]


def available_metric_ids() -> set[str]:
    return {metric.id for metric in get_metrics()}


def available_strategy_ids() -> set[str]:
    return {strategy.id for strategy in get_strategies()}


def list_backtest_symbols() -> list[str]:
    payload = invoke_runner("list-symbols")
    symbols = payload.get("symbols", [])
    return [str(symbol) for symbol in symbols]
