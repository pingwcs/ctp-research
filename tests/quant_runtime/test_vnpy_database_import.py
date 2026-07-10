"""Tests for vn.py historical bar database freshness."""

from datetime import datetime, timedelta, timezone
from types import ModuleType, SimpleNamespace
import sys

import pandas as pd

from quant_runtime.adapters.vnpy import database as vnpy_database


class FakeExchange:
    def __init__(self, value: str) -> None:
        self.value = value


class FakeInterval:
    MINUTE = "minute"


class FakeDatabase:
    def __init__(self) -> None:
        self.delete_calls = 0
        self.saved_batches: list[list[object]] = []

    def delete_bar_data(self, symbol, exchange, interval) -> None:
        self.delete_calls += 1

    def save_bar_data(self, bars) -> None:
        self.saved_batches.append(list(bars))


def _install_fake_vnpy_modules(monkeypatch, fake_database: FakeDatabase) -> None:
    constant = ModuleType("vnpy.trader.constant")
    constant.Exchange = FakeExchange
    constant.Interval = FakeInterval

    database = ModuleType("vnpy.trader.database")
    database.get_database = lambda: fake_database

    monkeypatch.setitem(sys.modules, "vnpy.trader.constant", constant)
    monkeypatch.setitem(sys.modules, "vnpy.trader.database", database)


def _write_parquet(data_dir, close_price: float = 3660.0) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    shanghai = timezone(timedelta(hours=8))
    pd.DataFrame(
        [
            {
                "exchange": "SHFE",
                "symbol": "RB0909",
                "eob": datetime(2009, 3, 27, 9, 1, tzinfo=shanghai),
                "open": 3550.0,
                "high": 3662.0,
                "low": 3550.0,
                "close": close_price,
                "volume": 10528.0,
                "amount": 378617760.0,
                "position": 7910.0,
            },
            {
                "exchange": "SHFE",
                "symbol": "RB0909",
                "eob": datetime(2009, 3, 27, 9, 2, tzinfo=shanghai),
                "open": 3660.0,
                "high": 3670.0,
                "low": 3650.0,
                "close": close_price + 1,
                "volume": 1024.0,
                "amount": 100.0,
                "position": 8000.0,
            },
        ],
    ).to_parquet(data_dir / "RB0909.parquet", index=False)


def _configure_import(monkeypatch, tmp_path, fake_database: FakeDatabase) -> None:
    _install_fake_vnpy_modules(monkeypatch, fake_database)
    monkeypatch.setattr(vnpy_database, "prepare_vnpy_runtime", lambda: None)
    monkeypatch.setattr(vnpy_database, "_to_vnpy_bar", lambda bar: bar)
    monkeypatch.setattr(
        vnpy_database,
        "settings",
        SimpleNamespace(runtime_dir=tmp_path / "runtime"),
        raising=False,
    )


def test_import_symbol_bars_reuses_fresh_database_for_same_symbol_and_range(
    tmp_path,
    monkeypatch,
):
    data_dir = tmp_path / "1min"
    _write_parquet(data_dir)
    fake_database = FakeDatabase()
    _configure_import(monkeypatch, tmp_path, fake_database)

    first_count = vnpy_database.import_symbol_bars("RB0909", data_dir)
    second_count = vnpy_database.import_symbol_bars("RB0909", data_dir)

    assert first_count == 2
    assert second_count == 2
    assert fake_database.delete_calls == 1
    assert len(fake_database.saved_batches) == 1


def test_import_symbol_bars_reimports_when_source_parquet_changes(
    tmp_path,
    monkeypatch,
):
    data_dir = tmp_path / "1min"
    _write_parquet(data_dir)
    fake_database = FakeDatabase()
    _configure_import(monkeypatch, tmp_path, fake_database)

    vnpy_database.import_symbol_bars("RB0909", data_dir)
    vnpy_database.import_symbol_bars("RB0909", data_dir)
    _write_parquet(data_dir, close_price=3700.0)
    changed_count = vnpy_database.import_symbol_bars("RB0909", data_dir)

    assert changed_count == 2
    assert fake_database.delete_calls == 2
    assert len(fake_database.saved_batches) == 2


def test_prepare_symbol_bars_returns_range_bars_and_reuses_fresh_database(
    tmp_path,
    monkeypatch,
):
    data_dir = tmp_path / "1min"
    _write_parquet(data_dir)
    fake_database = FakeDatabase()
    _configure_import(monkeypatch, tmp_path, fake_database)
    shanghai = timezone(timedelta(hours=8))
    start_time = datetime(2009, 3, 27, 9, 2, tzinfo=shanghai)
    end_time = datetime(2009, 3, 27, 9, 2, tzinfo=shanghai)

    first_bars = vnpy_database.prepare_symbol_bars(
        "RB0909",
        data_dir,
        start_time,
        end_time,
    )
    cached_bars = vnpy_database.prepare_symbol_bars(
        "RB0909",
        data_dir,
        start_time,
        end_time,
    )

    assert [bar.close_price for bar in first_bars] == [3661.0]
    assert [bar.close_price for bar in cached_bars] == [3661.0]
    assert fake_database.delete_calls == 1
    assert len(fake_database.saved_batches) == 1
