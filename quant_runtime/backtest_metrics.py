"""Backtest metric calculations."""

from collections.abc import Sequence
from math import sqrt
from typing import Any

from quant_runtime.backtest_config import MetricConfig
from quant_runtime.contracts import EquityPoint


ANNUALIZATION_DAYS = 240


def _stat_number(stats: dict[str, Any], key: str) -> float | None:
    value = stats.get(key)
    if value is None:
        return None
    return float(value)


def _configured_stat_value(stats: dict[str, Any], metric: MetricConfig) -> float | None:
    value = _stat_number(stats, metric.stats_key)
    if value is None:
        return None
    number = value / metric.divisor
    if metric.absolute:
        number = abs(number)
    return number * metric.sign


def _annual_return(stats: dict[str, Any]) -> float | None:
    value = _stat_number(stats, "annual_return")
    if value is None:
        return None
    return value / 100.0


def _max_drawdown(stats: dict[str, Any]) -> float | None:
    value = _stat_number(stats, "max_ddpercent")
    if value is None:
        return None
    return abs(value) / 100.0


def _daily_returns(equity_curve: Sequence[EquityPoint]) -> list[float]:
    returns: list[float] = []
    for previous, current in zip(equity_curve, equity_curve[1:]):
        if previous.equity == 0:
            continue
        returns.append((current.equity - previous.equity) / previous.equity)
    return returns


def _population_std(values: Sequence[float]) -> float | None:
    if not values:
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return sqrt(variance)


def _calmar(stats: dict[str, Any]) -> float | None:
    annual_return = _annual_return(stats)
    max_drawdown = _max_drawdown(stats)
    if annual_return is None or not max_drawdown:
        return None
    return annual_return / max_drawdown


def _profit_factor(daily_net_pnl: Sequence[float]) -> float | None:
    gross_profit = sum(value for value in daily_net_pnl if value > 0)
    gross_loss = abs(sum(value for value in daily_net_pnl if value < 0))
    if not gross_loss:
        return None
    return gross_profit / gross_loss


def _sortino(stats: dict[str, Any], equity_curve: Sequence[EquityPoint]) -> float | None:
    annual_return = _annual_return(stats)
    returns = _daily_returns(equity_curve)
    if annual_return is None or not returns:
        return None

    downside_variance = sum(min(0.0, value) ** 2 for value in returns) / len(returns)
    downside_deviation = sqrt(downside_variance) * sqrt(ANNUALIZATION_DAYS)
    if not downside_deviation:
        return None
    return annual_return / downside_deviation


def _information_ratio(stats: dict[str, Any], equity_curve: Sequence[EquityPoint]) -> float | None:
    annual_return = _annual_return(stats)
    return_std = _population_std(_daily_returns(equity_curve))
    if annual_return is None or not return_std:
        return None
    return annual_return / (return_std * sqrt(ANNUALIZATION_DAYS))


def metric_value(
    stats: dict[str, Any],
    metric: MetricConfig,
    equity_curve: Sequence[EquityPoint],
    daily_net_pnl: Sequence[float],
) -> float | None:
    configured = _configured_stat_value(stats, metric)
    if configured is not None:
        return configured

    if metric.id == "calmar":
        return _calmar(stats)
    if metric.id == "profit_factor":
        return _profit_factor(daily_net_pnl)
    if metric.id == "sortino":
        return _sortino(stats, equity_curve)
    if metric.id == "information_ratio":
        return _information_ratio(stats, equity_curve)

    return None
