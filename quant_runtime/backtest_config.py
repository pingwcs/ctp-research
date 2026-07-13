"""Backtest business configuration loaded from JSON.

业务功能: 从 backtest.json 加载默认策略、引擎参数、策略列表和指标列表。
算法要点: 运行时配置是策略/指标元数据的单一来源，加载时校验必填字段、
id 唯一性和 default_strategy 引用关系。
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from global_config import (
    DEFAULT_QUANT_RUNTIME_BACKTEST_CONFIG_PATH,
    load_environment_config,
)


DEFAULT_CONFIG_PATH = DEFAULT_QUANT_RUNTIME_BACKTEST_CONFIG_PATH


@dataclass(frozen=True)
class StrategyConfig:
    """业务功能: 描述一个可执行策略及其所属回测引擎。"""

    id: str
    name: str
    description: str
    engine: str
    class_path: str


@dataclass(frozen=True)
class MetricConfig:
    """业务功能: 描述一个可输出指标及其在引擎统计结果中的取值规则。"""

    id: str
    name: str
    description: str
    stats_key: str
    divisor: float = 1.0
    sign: float = 1.0
    absolute: bool = False


@dataclass(frozen=True)
class EngineConfig:
    """业务功能: 描述 vn.py BacktestingEngine 所需的账户和合约参数。"""

    initial_cash: float
    contract_size: int
    rate: float
    slippage: float
    price_tick: float


@dataclass(frozen=True)
class BacktestConfig:
    """业务功能: 一份完整回测业务配置的不可变快照。"""

    default_strategy: str
    engine: EngineConfig
    strategies: tuple[StrategyConfig, ...]
    metrics: tuple[MetricConfig, ...]

    def strategy(self, strategy_id: str) -> StrategyConfig:
        """业务功能: 按 id 查找策略配置。"""
        for strategy in self.strategies:
            if strategy.id == strategy_id:
                return strategy
        raise KeyError(strategy_id)

    def metric(self, metric_id: str) -> MetricConfig:
        """业务功能: 按 id 查找指标配置。"""
        for metric in self.metrics:
            if metric.id == metric_id:
                return metric
        raise KeyError(metric_id)


_cached_path: Path | None = None
_cached_config: BacktestConfig | None = None


def _config_path() -> Path:
    """业务功能: 解析当前环境使用的 backtest.json 路径。"""
    return load_environment_config().quant_runtime_backtest_config


def _required_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    """算法要点: 校验配置字段必须是 JSON object。"""
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"backtest config field {key!r} must be an object")
    return value


def _required_list(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """算法要点: 校验配置字段必须是 object 列表。"""
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"backtest config field {key!r} must be a list of objects")
    return value


def _required_str(payload: dict[str, Any], key: str) -> str:
    """算法要点: 校验配置字段必须是非空字符串。"""
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"backtest config field {key!r} must be a non-empty string")
    return value


def _load_from_path(path: Path) -> BacktestConfig:
    """业务功能: 从 JSON 文件加载并校验回测业务配置。

    算法要点: 将数字字段强制转换为 float/int；策略和指标 id 必须唯一，
    默认策略必须能在策略表中找到。
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("backtest config must be a JSON object")

    engine_payload = _required_mapping(payload, "engine")
    engine = EngineConfig(
        initial_cash=float(engine_payload["initial_cash"]),
        contract_size=int(engine_payload["contract_size"]),
        rate=float(engine_payload["rate"]),
        slippage=float(engine_payload["slippage"]),
        price_tick=float(engine_payload["price_tick"]),
    )

    strategies = tuple(
        StrategyConfig(
            id=_required_str(item, "id"),
            name=_required_str(item, "name"),
            description=_required_str(item, "description"),
            engine=_required_str(item, "engine"),
            class_path=_required_str(item, "class_path"),
        )
        for item in _required_list(payload, "strategies")
    )
    metrics = tuple(
        MetricConfig(
            id=_required_str(item, "id"),
            name=_required_str(item, "name"),
            description=_required_str(item, "description"),
            stats_key=_required_str(item, "stats_key"),
            divisor=float(item.get("divisor", 1.0)),
            sign=float(item.get("sign", 1.0)),
            absolute=bool(item.get("absolute", False)),
        )
        for item in _required_list(payload, "metrics")
    )
    default_strategy = _required_str(payload, "default_strategy")

    strategy_ids = {strategy.id for strategy in strategies}
    metric_ids = {metric.id for metric in metrics}
    if len(strategy_ids) != len(strategies):
        raise ValueError("backtest config strategy ids must be unique")
    if len(metric_ids) != len(metrics):
        raise ValueError("backtest config metric ids must be unique")
    if default_strategy not in strategy_ids:
        raise ValueError("backtest config default_strategy must reference a strategy")

    return BacktestConfig(
        default_strategy=default_strategy,
        engine=engine,
        strategies=strategies,
        metrics=metrics,
    )


def clear_backtest_config_cache() -> None:
    """业务功能: 清空配置缓存，供测试或热更新后重新加载。"""
    global _cached_config, _cached_path
    _cached_config = None
    _cached_path = None


def load_backtest_config() -> BacktestConfig:
    """业务功能: 加载当前 backtest.json，并按路径缓存结果。"""
    global _cached_config, _cached_path
    path = _config_path()
    if _cached_config is not None and _cached_path == path:
        return _cached_config

    _cached_config = _load_from_path(path)
    _cached_path = path
    return _cached_config


def default_strategy_id() -> str:
    """业务功能: 返回配置中的默认策略 id。"""
    return load_backtest_config().default_strategy
