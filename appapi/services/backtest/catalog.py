"""Backtest metadata and symbol discovery via quant runtime runner.

业务功能: 为 HTTP 接口提供策略、指标和可回测合约列表。
算法要点: 策略和指标的权威来源在 quant_runtime，本模块只读取和转换，
避免 appapi 持有重复常量。
"""

from appapi.schemas.backtest import MetricInfo, StrategyInfo
from appapi.services.backtest.metadata_cache import runtime_metadata
from appapi.services.backtest.runner_client import invoke_runner


def get_strategies() -> list[StrategyInfo]:
    """业务功能: 获取运行时策略列表并校验成 HTTP schema。"""
    payload = runtime_metadata()
    return [StrategyInfo.model_validate(item) for item in payload.get("strategies", [])]


def get_metrics() -> list[MetricInfo]:
    """业务功能: 获取运行时指标列表并校验成 HTTP schema。"""
    payload = runtime_metadata()
    return [MetricInfo.model_validate(item) for item in payload.get("metrics", [])]


def available_metric_ids() -> set[str]:
    """业务功能: 返回可用于请求校验或 UI 过滤的指标 id 集合。"""
    return {metric.id for metric in get_metrics()}


def available_strategy_ids() -> set[str]:
    """业务功能: 返回可用于请求校验或 UI 过滤的策略 id 集合。"""
    return {strategy.id for strategy in get_strategies()}


def list_backtest_symbols() -> list[str]:
    """业务功能: 通过运行时扫描 1 分钟 parquet 合约列表。"""
    payload = invoke_runner("list-symbols")
    symbols = payload.get("symbols", [])
    return [str(symbol) for symbol in symbols]
