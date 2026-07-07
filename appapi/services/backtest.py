"""Event-driven backtest service for MA cross futures strategies."""

from __future__ import annotations

from datetime import datetime
from math import floor, sqrt
from pathlib import Path

import duckdb
from fastapi import HTTPException, status
from loguru import logger

from appapi.core.config import settings
from appapi.schemas.backtest import (
    BacktestRunRequest,
    BacktestRunResponse,
    BacktestTrade,
    EquityPoint,
    MetricInfo,
    StrategyInfo,
)
from appapi.services.market_data import (
    _column_map,
    _describe_columns,
    _quote_identifier,
    _resolve_contract_file,
)


INITIAL_CASH = 100_000.0
MAX_TRADE_VALUE = 50_000.0
TARGET_CASH_FRACTION = 0.5
STOP_LOSS_PCT = 0.10

STRATEGIES = [
    StrategyInfo(
        id="ma_cross",
        name="MA5/MA20 Cross",
        description="Buy on MA5 crossing above MA20, sell on MA5 crossing below MA20.",
    ),
]

METRICS = [
    MetricInfo(id="total_return", name="Total Return", description="Total equity return."),
    MetricInfo(id="annual_return", name="Annual Return", description="Annualized return."),
    MetricInfo(id="sharpe", name="Sharpe Ratio", description="Annualized Sharpe ratio."),
    MetricInfo(id="max_drawdown", name="Max Drawdown", description="Largest equity drawdown."),
    MetricInfo(id="win_rate", name="Win Rate", description="Winning sell trades ratio."),
]


def list_backtest_symbols() -> list[str]:
    data_dir = settings.data_dir.resolve()
    if not data_dir.exists():
        return []
    return sorted(path.stem for path in data_dir.glob("RB*.parquet") if path.is_file())


def _to_epoch(value: datetime | None) -> int | None:
    if value is None:
        return None
    return int(value.timestamp())


def _build_backtest_sql(
    parquet_path: Path,
    mapped: dict[str, str],
    start_epoch: int | None,
    end_epoch: int | None,
) -> str:
    time_column = _quote_identifier(mapped["time"])
    close_column = _quote_identifier(mapped["close"])
    where_clauses = [
        f"{time_column} IS NOT NULL",
        f"{close_column} IS NOT NULL",
    ]
    if start_epoch is not None:
        where_clauses.append(f"epoch(CAST({time_column} AS TIMESTAMP)) >= {start_epoch}")
    if end_epoch is not None:
        where_clauses.append(f"epoch(CAST({time_column} AS TIMESTAMP)) <= {end_epoch}")

    return f"""
        SELECT
            epoch(CAST({time_column} AS TIMESTAMP))::BIGINT AS time,
            CAST({close_column} AS DOUBLE) AS close,
            AVG(CAST({close_column} AS DOUBLE)) OVER (
                ORDER BY {time_column} ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ) AS fallback_ma5,
            AVG(CAST({close_column} AS DOUBLE)) OVER (
                ORDER BY {time_column} ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) AS fallback_ma20,
            {'CAST(' + _quote_identifier(mapped['ma5']) + ' AS DOUBLE)' if 'ma5' in mapped else 'NULL'} AS file_ma5,
            {'CAST(' + _quote_identifier(mapped['ma20']) + ' AS DOUBLE)' if 'ma20' in mapped else 'NULL'} AS file_ma20
        FROM read_parquet('{str(parquet_path).replace("'", "''")}')
        WHERE {' AND '.join(where_clauses)}
        ORDER BY {time_column}
    """


def _extend_indicator_columns(columns: list[str], mapped: dict[str, str]) -> dict[str, str]:
    by_lower = {column.lower(): column for column in columns}
    extended = dict(mapped)
    if "ma5" in by_lower:
        extended["ma5"] = by_lower["ma5"]
    if "ma20" in by_lower:
        extended["ma20"] = by_lower["ma20"]
    return extended


def _load_rows(request: BacktestRunRequest) -> list[tuple[int, float, float, float]]:
    parquet_path = _resolve_contract_file(request.symbol)
    start_epoch = _to_epoch(request.start_time)
    end_epoch = _to_epoch(request.end_time)
    if start_epoch is not None and end_epoch is not None and start_epoch > end_epoch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be before end_time",
        )

    try:
        with duckdb.connect(database=":memory:", read_only=False) as connection:
            columns = _describe_columns(connection, parquet_path)
            mapped = _extend_indicator_columns(columns, _column_map(columns))
            rows = connection.execute(
                _build_backtest_sql(parquet_path, mapped, start_epoch, end_epoch),
            ).fetchall()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to load backtest rows for {}", request.symbol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"failed to load backtest data: {exc}",
        ) from exc

    normalized = []
    for time_value, close, fallback_ma5, fallback_ma20, file_ma5, file_ma20 in rows:
        ma5 = float(file_ma5 if file_ma5 is not None else fallback_ma5)
        ma20 = float(file_ma20 if file_ma20 is not None else fallback_ma20)
        normalized.append((int(time_value), float(close), ma5, ma20))
    return normalized


def _safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _fallback_metrics(
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
        sum((value - mean_return) ** 2 for value in returns) / max(1, len(returns) - 1)
        if returns
        else 0.0
    )
    sharpe = mean_return / sqrt(variance) * sqrt(252 * 48) if variance > 0 else None

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
    years = max((last_time - first_time) / (365.25 * 24 * 3600), 1 / 365.25)
    annual_return = (1 + total_return) ** (1 / years) - 1 if total_return is not None else None

    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "win_rate": _safe_div(wins, len(sell_trades)),
    }


def _quantstats_metrics(equity_curve: list[EquityPoint]) -> dict[str, float | None]:
    try:
        import pandas as pd
        import quantstats as qs
    except Exception:
        return {}

    if len(equity_curve) < 2:
        return {}

    series = pd.Series(
        [point.equity for point in equity_curve],
        index=pd.to_datetime([point.time for point in equity_curve], unit="s", utc=True),
        dtype="float64",
    )
    returns = series.pct_change().dropna()
    if returns.empty:
        return {}

    def call(metric_name: str):
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


def _selected_metrics(
    requested: list[str],
    equity_curve: list[EquityPoint],
    trades: list[BacktestTrade],
) -> dict[str, float | None]:
    available_ids = {metric.id for metric in METRICS}
    selected = requested or sorted(available_ids)
    invalid = [metric for metric in selected if metric not in available_ids]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported metrics: {', '.join(invalid)}",
        )

    values = _fallback_metrics(equity_curve, trades)
    values.update({k: v for k, v in _quantstats_metrics(equity_curve).items() if v is not None})
    return {metric: values.get(metric) for metric in selected}


def run_backtest(request: BacktestRunRequest) -> BacktestRunResponse:
    if request.strategy != "ma_cross":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported strategy: {request.strategy}",
        )

    rows = _load_rows(request)
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no bars found for the requested symbol and time range",
        )

    cash = INITIAL_CASH
    position = 0
    entry_price = 0.0
    trades: list[BacktestTrade] = []
    equity_curve: list[EquityPoint] = []
    previous_state: int | None = None

    for time_value, close, ma5, ma20 in rows:
        current_state = 1 if ma5 >= ma20 else -1
        should_buy = previous_state == -1 and current_state == 1 and position == 0
        should_sell = previous_state == 1 and current_state == -1 and position > 0
        stop_loss = position > 0 and entry_price > 0 and (entry_price - close) / entry_price >= STOP_LOSS_PCT

        if should_buy:
            buy_price = close + 1
            target_value = min(cash * TARGET_CASH_FRACTION, MAX_TRADE_VALUE)
            quantity = floor(target_value / buy_price)
            if quantity > 0:
                cash -= quantity * buy_price
                position += quantity
                entry_price = buy_price
                trades.append(
                    BacktestTrade(
                        time=time_value,
                        side="buy",
                        price=buy_price,
                        quantity=quantity,
                        cash=cash,
                        reason="ma_cross_up",
                    ),
                )

        if should_sell or stop_loss:
            sell_price = close - 1
            cash += position * sell_price
            trades.append(
                BacktestTrade(
                    time=time_value,
                    side="sell",
                    price=sell_price,
                    quantity=position,
                    cash=cash,
                    reason="stop_loss" if stop_loss else "ma_cross_down",
                ),
            )
            position = 0
            entry_price = 0.0

        position_value = position * close
        equity_curve.append(
            EquityPoint(
                time=time_value,
                equity=cash + position_value,
                cash=cash,
                position_value=position_value,
                position=position,
            ),
        )
        previous_state = current_state

    if position > 0:
        last_time, last_close, _, _ = rows[-1]
        sell_price = last_close - 1
        cash += position * sell_price
        trades.append(
            BacktestTrade(
                time=last_time,
                side="sell",
                price=sell_price,
                quantity=position,
                cash=cash,
                reason="contract_expiry",
            ),
        )
        equity_curve[-1] = EquityPoint(
            time=last_time,
            equity=cash,
            cash=cash,
            position_value=0.0,
            position=0,
        )

    metrics = _selected_metrics(request.metrics, equity_curve, trades)
    return BacktestRunResponse(
        symbol=request.symbol,
        strategy=request.strategy,
        initial_cash=INITIAL_CASH,
        final_equity=equity_curve[-1].equity,
        trades=trades,
        equity_curve=equity_curve,
        metrics=metrics,
    )
