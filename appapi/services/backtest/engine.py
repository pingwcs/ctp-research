"""Trading engine for supported backtest strategies."""

from math import floor

from fastapi import HTTPException, status

from appapi.schemas.backtest import (
    BacktestRunRequest,
    BacktestRunResponse,
    BacktestTrade,
    EquityPoint,
)
from appapi.services.backtest.metrics import selected_metrics
from appapi.services.backtest.repository import load_rows


INITIAL_CASH = 100_000.0
MAX_TRADE_VALUE = 50_000.0
TARGET_CASH_FRACTION = 0.5
STOP_LOSS_PCT = 0.10


def run_backtest(request: BacktestRunRequest) -> BacktestRunResponse:
    if request.strategy != "ma_cross":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported strategy: {request.strategy}",
        )

    rows = load_rows(request)
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

    for row in rows:
        current_state = 1 if row.ma5 >= row.ma20 else -1
        should_buy = (
            previous_state == -1
            and current_state == 1
            and position == 0
        )
        should_sell = (
            previous_state == 1
            and current_state == -1
            and position > 0
        )
        stop_loss = (
            position > 0
            and entry_price > 0
            and (entry_price - row.close) / entry_price >= STOP_LOSS_PCT
        )

        if should_buy:
            buy_price = row.close + 1
            target_value = min(cash * TARGET_CASH_FRACTION, MAX_TRADE_VALUE)
            quantity = floor(target_value / buy_price)
            if quantity > 0:
                cash -= quantity * buy_price
                position += quantity
                entry_price = buy_price
                trades.append(
                    BacktestTrade(
                        time=row.time,
                        side="buy",
                        price=buy_price,
                        quantity=quantity,
                        cash=cash,
                        reason="ma_cross_up",
                    ),
                )

        if should_sell or stop_loss:
            sell_price = row.close - 1
            cash += position * sell_price
            trades.append(
                BacktestTrade(
                    time=row.time,
                    side="sell",
                    price=sell_price,
                    quantity=position,
                    cash=cash,
                    reason="stop_loss" if stop_loss else "ma_cross_down",
                ),
            )
            position = 0
            entry_price = 0.0

        position_value = position * row.close
        equity_curve.append(
            EquityPoint(
                time=row.time,
                equity=cash + position_value,
                cash=cash,
                position_value=position_value,
                position=position,
            ),
        )
        previous_state = current_state

    if position > 0:
        last_bar = rows[-1]
        sell_price = last_bar.close - 1
        cash += position * sell_price
        trades.append(
            BacktestTrade(
                time=last_bar.time,
                side="sell",
                price=sell_price,
                quantity=position,
                cash=cash,
                reason="contract_expiry",
            ),
        )
        equity_curve[-1] = EquityPoint(
            time=last_bar.time,
            equity=cash,
            cash=cash,
            position_value=0.0,
            position=0,
        )

    metrics = selected_metrics(request.metrics, equity_curve, trades)
    return BacktestRunResponse(
        symbol=request.symbol,
        strategy=request.strategy,
        initial_cash=INITIAL_CASH,
        final_equity=equity_curve[-1].equity,
        trades=trades,
        equity_curve=equity_curve,
        metrics=metrics,
    )
