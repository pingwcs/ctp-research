"""Tests for derived backtest equity metrics."""

from math import sqrt

import pytest

from quant_runtime.backtest_config import MetricConfig
from quant_runtime.backtest_metrics import metric_value
from quant_runtime.contracts import EquityPoint


def _point(index: int, equity: float) -> EquityPoint:
    return EquityPoint(
        time=1_700_000_000 + index * 86_400,
        equity=equity,
        cash=equity,
        position_value=0.0,
        position=0,
    )


def test_metric_value_derives_equity_curve_ratios_when_stats_are_missing():
    stats = {"annual_return": 24.0, "max_ddpercent": -12.0}
    equity_curve = [
        _point(0, 100_000.0),
        _point(1, 104_000.0),
        _point(2, 101_920.0),
        _point(3, 107_016.0),
    ]
    daily_net_pnl = [4_000.0, -2_080.0, 5_096.0]

    assert metric_value(
        stats,
        MetricConfig(
            id="calmar",
            name="Calmar Ratio",
            description="Annual return divided by maximum drawdown.",
            stats_key="return_drawdown_ratio",
        ),
        equity_curve,
        daily_net_pnl,
    ) == pytest.approx(2.0)
    assert metric_value(
        stats,
        MetricConfig(
            id="profit_factor",
            name="Profit Factor",
            description="Gross profit divided by gross loss.",
            stats_key="profit_factor",
        ),
        equity_curve,
        daily_net_pnl,
    ) == pytest.approx((4_000.0 + 5_096.0) / 2_080.0)

    daily_returns = [0.04, -0.02, 0.05]
    downside_deviation = sqrt((0.02**2) / len(daily_returns)) * sqrt(240)
    return_std = sqrt(
        sum((value - (sum(daily_returns) / len(daily_returns))) ** 2 for value in daily_returns)
        / len(daily_returns),
    )
    information_denominator = return_std * sqrt(240)

    assert metric_value(
        stats,
        MetricConfig(
            id="sortino",
            name="Sortino Ratio",
            description="Return adjusted by downside volatility.",
            stats_key="sortino_ratio",
        ),
        equity_curve,
        daily_net_pnl,
    ) == pytest.approx(0.24 / downside_deviation)
    assert metric_value(
        stats,
        MetricConfig(
            id="information_ratio",
            name="Information Ratio",
            description="Excess return adjusted by tracking error.",
            stats_key="information_ratio",
        ),
        equity_curve,
        daily_net_pnl,
    ) == pytest.approx(0.24 / information_denominator)
