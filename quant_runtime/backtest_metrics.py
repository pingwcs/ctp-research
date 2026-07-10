"""Backtest metric calculations.

业务功能: 将 vn.py 统计结果、权益曲线和每日净盈亏转换成配置化绩效指标。
算法要点: 优先使用 backtest.json 中 stats_key 指向的引擎原生统计值；引擎
没有提供时，再用权益曲线或 daily_net_pnl 计算 Calmar、Profit Factor、
Sortino 和 Information Ratio。
"""

from collections.abc import Sequence
from math import sqrt
from typing import Any

from quant_runtime.backtest_config import MetricConfig
from quant_runtime.contracts import EquityPoint


ANNUALIZATION_DAYS = 240


def _stat_number(stats: dict[str, Any], key: str) -> float | None:
    """算法要点: 从 vn.py stats 中安全读取数值字段。"""
    value = stats.get(key)
    if value is None:
        return None
    return float(value)


def _configured_stat_value(stats: dict[str, Any], metric: MetricConfig) -> float | None:
    """业务功能: 按配置的 divisor/sign/absolute 规则转换引擎原生指标。"""
    value = _stat_number(stats, metric.stats_key)
    if value is None:
        return None
    number = value / metric.divisor
    if metric.absolute:
        number = abs(number)
    return number * metric.sign


def _annual_return(stats: dict[str, Any]) -> float | None:
    """算法要点: vn.py annual_return 为百分数，这里转成小数收益率。"""
    value = _stat_number(stats, "annual_return")
    if value is None:
        return None
    return value / 100.0


def _max_drawdown(stats: dict[str, Any]) -> float | None:
    """算法要点: vn.py max_ddpercent 为百分数且可能为负，这里转绝对小数。"""
    value = _stat_number(stats, "max_ddpercent")
    if value is None:
        return None
    return abs(value) / 100.0


def _daily_returns(equity_curve: Sequence[EquityPoint]) -> list[float]:
    """算法要点: 用相邻权益点计算日收益率，跳过前一权益为 0 的异常点。"""
    returns: list[float] = []
    for previous, current in zip(equity_curve, equity_curve[1:]):
        if previous.equity == 0:
            continue
        returns.append((current.equity - previous.equity) / previous.equity)
    return returns


def _population_std(values: Sequence[float]) -> float | None:
    """算法要点: 使用总体标准差，适配完整回测样本序列。"""
    if not values:
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return sqrt(variance)


def _calmar(stats: dict[str, Any]) -> float | None:
    """算法要点: Calmar = 年化收益率 / 最大回撤。"""
    annual_return = _annual_return(stats)
    max_drawdown = _max_drawdown(stats)
    if annual_return is None or not max_drawdown:
        return None
    return annual_return / max_drawdown


def _profit_factor(daily_net_pnl: Sequence[float]) -> float | None:
    """算法要点: Profit Factor = 总盈利 / abs(总亏损)。"""
    gross_profit = sum(value for value in daily_net_pnl if value > 0)
    gross_loss = abs(sum(value for value in daily_net_pnl if value < 0))
    if not gross_loss:
        return None
    return gross_profit / gross_loss


def _sortino(stats: dict[str, Any], equity_curve: Sequence[EquityPoint]) -> float | None:
    """算法要点: Sortino 用下行波动率而非全样本波动率调整年化收益。"""
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
    """算法要点: 未接入基准收益时，用权益日收益标准差近似跟踪误差。"""
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
    """业务功能: 计算一个已配置指标的最终输出值。"""
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
