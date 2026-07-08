"""Backtest metric calculations."""

from math import sqrt

from fastapi import HTTPException, status

from appapi.schemas.backtest import BacktestTrade, EquityPoint
from appapi.services.backtest.catalog import available_metric_ids


def safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def fallback_metrics(
    equity_curve: list[EquityPoint],
    trades: list[BacktestTrade],
) -> dict[str, float | None]:
    if not equity_curve:
        return {
            "total_return": None,
            "annual_return": None,
            "sharpe": None,
            "max_drawdown": None,
            "win_rate": None,
        }

    equities = [point.equity for point in equity_curve]
    returns = [
        (equities[index] / equities[index - 1]) - 1
        for index in range(1, len(equities))
        if equities[index - 1] > 0
    ]
    total_return = (equities[-1] / equities[0]) - 1 if equities[0] else None
    mean_return = sum(returns) / len(returns) if returns else 0.0
    variance = (
        sum((value - mean_return) ** 2 for value in returns)
        / max(1, len(returns) - 1)
        if returns
        else 0.0
    )
    sharpe = (
        mean_return / sqrt(variance) * sqrt(252 * 48)
        if variance > 0
        else None
    )

    peak = equities[0]
    max_drawdown = 0.0
    for equity in equities:
        peak = max(peak, equity)
        drawdown = (equity / peak) - 1 if peak else 0.0
        max_drawdown = min(max_drawdown, drawdown)

    sell_trades = [trade for trade in trades if trade.side == "sell"]
    buy_prices: list[float] = []
    wins = 0
    for trade in trades:
        if trade.side == "buy":
            buy_prices.append(trade.price)
        elif buy_prices:
            entry = buy_prices.pop(0)
            if trade.price > entry:
                wins += 1

    first_time = equity_curve[0].time
    last_time = equity_curve[-1].time
    seconds_per_year = 365.25 * 24 * 3600
    years = max((last_time - first_time) / seconds_per_year, 1 / 365.25)
    annual_return = (
        (1 + total_return) ** (1 / years) - 1
        if total_return is not None
        else None
    )

    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "win_rate": safe_div(wins, len(sell_trades)),
    }


def quantstats_metrics(
    equity_curve: list[EquityPoint],
) -> dict[str, float | None]:
    try:
        import pandas as pd
        import quantstats as qs
    except Exception:
        return {}

    if len(equity_curve) < 2:
        return {}

    series = pd.Series(
        [point.equity for point in equity_curve],
        index=pd.to_datetime(
            [point.time for point in equity_curve],
            unit="s",
            utc=True,
        ),
        dtype="float64",
    )
    returns = series.pct_change().dropna()
    if returns.empty:
        return {}

    def call(metric_name: str) -> float | None:
        try:
            value = getattr(qs.stats, metric_name)(returns)
            return float(value) if value is not None else None
        except Exception:
            return None

    return {
        "sharpe": call("sharpe"),
        "max_drawdown": call("max_drawdown"),
        "annual_return": call("cagr"),
    }


def selected_metrics(
    requested: list[str],
    equity_curve: list[EquityPoint],
    trades: list[BacktestTrade],
) -> dict[str, float | None]:
    available_ids = available_metric_ids()
    selected = requested or sorted(available_ids)
    invalid = [metric for metric in selected if metric not in available_ids]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported metrics: {', '.join(invalid)}",
        )

    values = fallback_metrics(equity_curve, trades)
    values.update(
        {
            key: value
            for key, value in quantstats_metrics(equity_curve).items()
            if value is not None
        },
    )
    return {metric: values.get(metric) for metric in selected}
