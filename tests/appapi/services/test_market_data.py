"""Tests for market-data service behavior."""

import pytest
from fastapi import HTTPException, status

from appapi.services.market_data import _marker_from_signal, load_kline_data


def test_load_kline_data_returns_last_page_when_offset_is_missing():
    response = load_kline_data("RB0909", limit=3)

    assert response.symbol == "RB0909"
    assert response.total == 5355
    assert response.offset == 5352
    assert response.limit == 3
    assert len(response.candles) == 3
    assert len(response.markers) == 0
    assert response.candles[0].time == 1253026200


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
