"""Tests for market-data service behavior."""

import pytest
import pandas as pd
from fastapi import HTTPException, status

from appapi.services.market_data import _marker_from_signal, load_kline_data


def _write_kline_parquet(tmp_path, monkeypatch, rows):
    market_root = tmp_path / "output"
    data_dir = market_root / "5min"
    data_dir.mkdir(parents=True)
    pd.DataFrame(rows).to_parquet(data_dir / "RB0909.parquet", index=False)
    monkeypatch.setattr(
        "appapi.services.parquet_utils.settings",
        type("Settings", (), {"data_dir": market_root})(),
    )


def test_load_kline_data_reads_canonical_5min_parquet(tmp_path, monkeypatch):
    _write_kline_parquet(
        tmp_path,
        monkeypatch,
        [
            {
                "eob": "2009-03-27 09:05:00+08:00",
                "open": 1.0,
                "high": 2.0,
                "low": 1.0,
                "close": 2.0,
                "volume": 3.0,
            },
        ],
    )

    response = load_kline_data("RB0909", limit=3)

    assert response.symbol == "RB0909"
    assert response.total == 1
    assert response.candles[0].close == 2.0


def test_load_kline_data_returns_last_page_when_offset_is_missing(tmp_path, monkeypatch):
    _write_kline_parquet(
        tmp_path,
        monkeypatch,
        [
            {
                "eob": f"2009-03-27 09:{minute:02d}:00+08:00",
                "open": float(minute),
                "high": float(minute + 1),
                "low": float(minute - 1),
                "close": float(minute),
                "volume": float(minute),
            }
            for minute in range(5)
        ],
    )

    response = load_kline_data("RB0909", limit=3)

    assert response.symbol == "RB0909"
    assert response.total == 5
    assert response.offset == 2
    assert response.limit == 3
    assert len(response.candles) == 3
    assert len(response.markers) == 0
    assert response.candles[0].close == 2.0


def test_load_kline_data_rejects_path_traversal_symbol():
    with pytest.raises(HTTPException) as exc_info:
        load_kline_data("../RB0909", limit=3)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


def test_marker_from_signal_maps_buy_and_sell_values():
    buy = _marker_from_signal(1, " buy ")
    sell = _marker_from_signal(2, "SELL")

    assert buy is not None
    assert buy.position == "belowBar"
    assert buy.shape == "arrowUp"
    assert buy.text == "Buy"

    assert sell is not None
    assert sell.position == "aboveBar"
    assert sell.shape == "arrowDown"
    assert sell.text == "Sell"
    assert _marker_from_signal(3, "hold") is None
