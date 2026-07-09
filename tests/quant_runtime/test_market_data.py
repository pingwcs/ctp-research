"""Tests for canonical parquet market data used by the quant runtime."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from quant_runtime.market_data import list_symbols, read_minute_bars


def test_list_symbols_reads_1min_parquet_files(tmp_path: Path):
    data_dir = tmp_path / "1min"
    data_dir.mkdir()
    pd.DataFrame(
        [
            {
                "exchange": "SHFE",
                "symbol": "RB0909",
                "eob": "2009-03-27 09:01:00+08:00",
                "open": 1.0,
                "high": 2.0,
                "low": 1.0,
                "close": 2.0,
                "volume": 3.0,
                "amount": 4.0,
                "position": 5.0,
            },
        ],
    ).to_parquet(data_dir / "RB0909.parquet", index=False)

    assert list_symbols(data_dir) == ["RB0909"]


def test_read_minute_bars_maps_canonical_parquet(tmp_path: Path):
    data_dir = tmp_path / "1min"
    data_dir.mkdir()
    pd.DataFrame(
        [
            {
                "exchange": "SHFE",
                "symbol": "RB0909",
                "eob": "2009-03-27 09:01:00+08:00",
                "open": 3550.0,
                "high": 3662.0,
                "low": 3550.0,
                "close": 3660.0,
                "volume": 10528.0,
                "amount": 378617760.0,
                "position": 7910.0,
            },
        ],
    ).to_parquet(data_dir / "RB0909.parquet", index=False)

    bars = read_minute_bars("RB0909", data_dir)

    assert len(bars) == 1
    assert bars[0].symbol == "RB0909"
    assert bars[0].exchange == "SHFE"
    assert bars[0].datetime == datetime(
        2009,
        3,
        27,
        9,
        1,
        tzinfo=timezone(timedelta(hours=8)),
    )
    assert bars[0].open_price == 3550.0
    assert bars[0].turnover == 378617760.0
    assert bars[0].open_interest == 7910.0


def test_read_minute_bars_treats_naive_range_as_bar_timezone(tmp_path: Path):
    data_dir = tmp_path / "1min"
    data_dir.mkdir()
    pd.DataFrame(
        [
            {
                "exchange": "SHFE",
                "symbol": "RB0909",
                "eob": "2009-04-01 09:01:00+08:00",
                "open": 3550.0,
                "high": 3662.0,
                "low": 3550.0,
                "close": 3660.0,
                "volume": 10528.0,
                "amount": 378617760.0,
                "position": 7910.0,
            },
        ],
    ).to_parquet(data_dir / "RB0909.parquet", index=False)

    bars = read_minute_bars(
        "RB0909",
        data_dir,
        start_time=datetime(2009, 4, 1, 9, 0),
        end_time=datetime(2009, 4, 1, 9, 2),
    )

    assert [bar.datetime.isoformat() for bar in bars] == ["2009-04-01T09:01:00+08:00"]
