import pytest
from fastapi import HTTPException

from appapi.api import market as market_api
from appapi.schemas.market import KLineResponse
from appapi.services.market_query import MAX_QUERY_ROWS, normalize_limit


def test_normalize_limit_caps_large_market_reads() -> None:
    assert normalize_limit(50_000) == MAX_QUERY_ROWS == 10_000


def test_normalize_limit_rejects_non_positive_values() -> None:
    with pytest.raises(ValueError, match="limit must be positive"):
        normalize_limit(0)


def test_kline_endpoint_caps_the_reader_limit(monkeypatch) -> None:
    seen: dict[str, int] = {}

    class Reader:
        def load(self, *, symbol: str, offset: int | None, limit: int) -> KLineResponse:
            seen["limit"] = limit
            return KLineResponse(symbol=symbol, total=0, offset=0, limit=limit, candles=[])

    monkeypatch.setattr(market_api, "get_kline_reader", lambda: Reader())

    response = market_api.get_kline(symbol="RB0909", limit=50_000)

    assert response.limit == MAX_QUERY_ROWS
    assert seen["limit"] == MAX_QUERY_ROWS


def test_kline_endpoint_rejects_non_positive_limit() -> None:
    with pytest.raises(HTTPException) as exc_info:
        market_api.get_kline(symbol="RB0909", limit=0)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "limit must be positive"
