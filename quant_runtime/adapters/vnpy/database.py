"""vn.py historical bar database import utilities."""

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from quant_runtime.contracts import RunnerError
from quant_runtime.market_data import MarketDataError, NormalizedBar, read_minute_bars
from quant_runtime.settings import prepare_vnpy_runtime


def _chunks(values: list[NormalizedBar], chunk_size: int) -> Iterable[list[NormalizedBar]]:
    for index in range(0, len(values), chunk_size):
        yield values[index : index + chunk_size]


def _to_vnpy_bar(bar: NormalizedBar):
    prepare_vnpy_runtime()

    from vnpy.trader.constant import Exchange, Interval
    from vnpy.trader.object import BarData

    return BarData(
        symbol=bar.symbol,
        exchange=Exchange(bar.exchange),
        datetime=bar.datetime,
        interval=Interval.MINUTE,
        volume=bar.volume,
        turnover=bar.turnover,
        open_interest=bar.open_interest,
        open_price=bar.open_price,
        high_price=bar.high_price,
        low_price=bar.low_price,
        close_price=bar.close_price,
        gateway_name="PARQUET",
    )


def import_symbol_bars(
    symbol: str,
    minute_data_dir: Path,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    chunk_size: int = 2000,
) -> int:
    prepare_vnpy_runtime()
    try:
        bars = read_minute_bars(symbol, minute_data_dir, start_time, end_time)
    except MarketDataError as exc:
        raise RunnerError(404, str(exc)) from exc
    if not bars:
        raise RunnerError(404, "no bars found for the requested symbol and time range")

    from vnpy.trader.constant import Exchange, Interval
    from vnpy.trader.database import get_database

    database = get_database()
    exchange = Exchange(bars[0].exchange)
    database.delete_bar_data(symbol, exchange, Interval.MINUTE)

    saved = 0
    for batch in _chunks(bars, chunk_size):
        database.save_bar_data([_to_vnpy_bar(bar) for bar in batch])
        saved += len(batch)
    return saved
