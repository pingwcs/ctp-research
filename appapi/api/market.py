"""Market-data HTTP endpoints."""

from fastapi import APIRouter, Query

from appapi.schemas.market import KLineResponse
from appapi.services.market_data import load_kline_data


router = APIRouter()


@router.get("/kline", response_model=KLineResponse)
def get_kline(
    symbol: str = Query(..., min_length=1, examples=["RB0909"]),
) -> KLineResponse:
    return load_kline_data(symbol=symbol)
