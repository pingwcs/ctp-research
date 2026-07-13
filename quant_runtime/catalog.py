"""Strategy and metric metadata owned by the quant runtime.

业务功能: 对外提供策略、指标、引擎配置和合约文件解析。
算法要点: catalog 只读取 backtest_config 的权威配置，并在请求进入回测前
完成策略 id、指标 id 和 symbol 路径安全校验。
"""

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
    """业务功能: 输出 appapi/UI 可展示的策略和指标元数据。"""
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
    """业务功能: 返回当前配置支持的指标 id 集合。"""
    return {metric.id for metric in load_backtest_config().metrics}


def strategy_ids() -> set[str]:
    """业务功能: 返回当前配置支持的策略 id 集合。"""
    return {strategy.id for strategy in load_backtest_config().strategies}


def clear_catalog_cache() -> None:
    """业务功能: 清空 catalog 底层配置缓存。"""
    clear_backtest_config_cache()


def engine_config() -> EngineConfig:
    """业务功能: 返回当前回测引擎参数配置。"""
    return load_backtest_config().engine


def metric_config(metric_id: str) -> MetricConfig:
    """业务功能: 获取单个指标配置。"""
    return load_backtest_config().metric(metric_id)


def strategy_config(strategy_id: str) -> StrategyConfig:
    """业务功能: 获取单个策略配置。"""
    return load_backtest_config().strategy(strategy_id)


def validate_symbol(symbol: str) -> None:
    """算法要点: 限制 symbol 字符集，避免被拼接成任意文件路径。"""
    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise RunnerError(
            400,
            "symbol may only contain letters, numbers, underscore, dash and dot",
        )


def validate_request_ids(strategy: str, metrics: list[str]) -> list[str]:
    """业务功能: 校验回测请求中的策略和指标 id。

    算法要点: 未传 metrics 时默认选择所有已配置指标；非法 id 一次性列出，
    便于调用方修正请求。
    """
    if strategy not in strategy_ids():
        raise RunnerError(400, f"unsupported strategy: {strategy}")

    selected = metrics or sorted(metric_ids())
    invalid = [metric for metric in selected if metric not in metric_ids()]
    if invalid:
        raise RunnerError(400, f"unsupported metrics: {', '.join(invalid)}")
    return selected


def symbol_parquet_path(symbol: str, data_dir: Path) -> Path:
    """业务功能: 将 symbol 解析为 1 分钟 parquet 文件路径。

    算法要点: resolve 后确认最终路径仍位于 data_dir 内，抵御路径穿越。
    """
    validate_symbol(symbol)
    root = data_dir.resolve()
    path = (root / f"{symbol}.parquet").resolve()
    if root not in path.parents:
        raise RunnerError(400, "invalid symbol path")
    if not path.exists():
        raise RunnerError(404, f"contract parquet not found: {path}")
    return path
