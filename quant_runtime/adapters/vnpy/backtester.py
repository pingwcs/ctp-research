"""Run vn.py backtests and return quant runtime domain results."""

from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from quant_runtime.adapters.vnpy.database import import_symbol_bars
from quant_runtime.catalog import validate_request_ids
from quant_runtime.contracts import (
    BacktestDomainResult,
    BacktestRequest,
    BacktestTrade,
    EquityPoint,
    RunnerError,
)
from quant_runtime.market_data import MarketDataError, read_minute_bars
from quant_runtime.settings import settings


INITIAL_CASH = 100_000.0
CONTRACT_SIZE = 1
RATE = 0.0
SLIPPAGE = 1.0
PRICE_TICK = 1.0


def _epoch(value: date | datetime) -> int:
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, time.min)
    return int(value.timestamp())


def _bars_for_symbol(symbol: str, minute_data_dir: Path):
    try:
        bars = read_minute_bars(symbol, minute_data_dir)
    except MarketDataError as exc:
        raise RunnerError(404, str(exc)) from exc
    if not bars:
        raise RunnerError(404, "no bars found for the requested symbol")
    return bars


def _metric_value(stats: dict[str, Any], metric: str) -> float | None:
    mapping = {
        "total_return": ("total_return", 100.0),
        "annual_return": ("annual_return", 100.0),
        "sharpe": ("sharpe_ratio", 1.0),
        "max_drawdown": ("max_ddpercent", -100.0),
        "win_rate": ("win_rate", 100.0),
    }
    key, divisor = mapping[metric]
    value = stats.get(key)
    if value is None:
        return None
    number = float(value)
    if metric == "max_drawdown":
        return -abs(number / 100.0)
    return number / divisor


def _build_equity_curve(engine) -> list[EquityPoint]:
    daily_df = getattr(engine, "daily_df", None)
    if daily_df is None or daily_df.empty:
        return []

    points: list[EquityPoint] = []
    for index, row in daily_df.iterrows():
        timestamp = index.to_pydatetime() if hasattr(index, "to_pydatetime") else index
        equity = float(row.get("balance", row.get("net_pnl", 0.0) + INITIAL_CASH))
        position = int(row.get("end_pos", 0) or 0)
        close_price = float(row.get("close_price", 0.0) or 0.0)
        position_value = position * close_price * CONTRACT_SIZE
        points.append(
            EquityPoint(
                time=_epoch(timestamp),
                equity=equity,
                cash=equity - position_value,
                position_value=position_value,
                position=position,
            ),
        )
    return points


def _build_trades(engine) -> list[BacktestTrade]:
    from vnpy.trader.constant import Direction

    trades: list[BacktestTrade] = []
    for trade in sorted(engine.trades.values(), key=lambda item: item.datetime):
        side = "buy" if trade.direction == Direction.LONG else "sell"
        trades.append(
            BacktestTrade(
                time=_epoch(trade.datetime),
                side=side,
                price=float(trade.price),
                quantity=int(trade.volume),
                cash=0.0,
                reason=str(getattr(trade, "offset", "")),
            ),
        )
    return trades


def run_backtest(
    request: BacktestRequest,
    minute_data_dir: Path = settings.minute_data_dir,
) -> BacktestDomainResult:
    selected_metrics = validate_request_ids(request.strategy, request.metrics)
    if (
        request.start_time is not None
        and request.end_time is not None
        and request.start_time > request.end_time
    ):
        raise RunnerError(400, "start_time must be before end_time")

    bars = _bars_for_symbol(request.symbol, minute_data_dir)
    import_symbol_bars(
        request.symbol,
        minute_data_dir,
        request.start_time,
        request.end_time,
    )

    from quant_runtime.adapters.vnpy.strategies.ma_cross_strategy import MaCrossStrategy
    from vnpy.trader.constant import Exchange, Interval
    from vnpy_ctastrategy.backtesting import BacktestingEngine

    start = request.start_time or bars[0].datetime
    end = request.end_time or bars[-1].datetime

    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol=f"{request.symbol}.{Exchange(bars[0].exchange).value}",
        interval=Interval.MINUTE,
        start=start,
        end=end,
        rate=RATE,
        slippage=SLIPPAGE,
        size=CONTRACT_SIZE,
        pricetick=PRICE_TICK,
        capital=INITIAL_CASH,
    )
    engine.add_strategy(MaCrossStrategy, {})
    engine.load_data()
    engine.run_backtesting()
    engine.calculate_result()
    stats = engine.calculate_statistics(output=False)

    equity_curve = _build_equity_curve(engine)
    trades = _build_trades(engine)
    metrics = {metric: _metric_value(stats, metric) for metric in selected_metrics}
    final_equity = equity_curve[-1].equity if equity_curve else INITIAL_CASH
    return BacktestDomainResult(
        symbol=request.symbol,
        strategy=request.strategy,
        engine="vnpy",
        initial_cash=INITIAL_CASH,
        final_equity=final_equity,
        trades=trades,
        equity_curve=equity_curve,
        metrics=metrics,
    )
