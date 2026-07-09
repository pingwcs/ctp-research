"""Backtest business configuration loaded from JSON."""

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
    id: str
    name: str
    description: str
    engine: str
    class_path: str


@dataclass(frozen=True)
class MetricConfig:
    id: str
    name: str
    description: str
    stats_key: str
    divisor: float = 1.0
    sign: float = 1.0
    absolute: bool = False


@dataclass(frozen=True)
class EngineConfig:
    initial_cash: float
    contract_size: int
    rate: float
    slippage: float
    price_tick: float


@dataclass(frozen=True)
class BacktestConfig:
    default_strategy: str
    engine: EngineConfig
    strategies: tuple[StrategyConfig, ...]
    metrics: tuple[MetricConfig, ...]

    def strategy(self, strategy_id: str) -> StrategyConfig:
        for strategy in self.strategies:
            if strategy.id == strategy_id:
                return strategy
        raise KeyError(strategy_id)

    def metric(self, metric_id: str) -> MetricConfig:
        for metric in self.metrics:
            if metric.id == metric_id:
                return metric
        raise KeyError(metric_id)


_cached_path: Path | None = None
_cached_config: BacktestConfig | None = None


def _config_path() -> Path:
    return load_environment_config().quant_runtime_backtest_config


def _required_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"backtest config field {key!r} must be an object")
    return value


def _required_list(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"backtest config field {key!r} must be a list of objects")
    return value


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"backtest config field {key!r} must be a non-empty string")
    return value


def _load_from_path(path: Path) -> BacktestConfig:
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
    global _cached_config, _cached_path
    _cached_config = None
    _cached_path = None


def load_backtest_config() -> BacktestConfig:
    global _cached_config, _cached_path
    path = _config_path()
    if _cached_config is not None and _cached_path == path:
        return _cached_config

    _cached_config = _load_from_path(path)
    _cached_path = path
    return _cached_config


def default_strategy_id() -> str:
    return load_backtest_config().default_strategy
