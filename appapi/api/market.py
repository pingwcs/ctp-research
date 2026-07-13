"""Market-data HTTP endpoints.

业务功能: 暴露 K 线查询 API，让前端按合约、偏移和窗口大小读取本地
parquet 行情。
算法要点: HTTP 层只声明参数约束，分页、字段识别和数据归一化由
services.market_data 处理。
"""

from fastapi import APIRouter, HTTPException, Query, status

from appapi.schemas.market import KLineResponse
from appapi.services.kline_reader import get_kline_reader
from appapi.services.market_query import normalize_limit


router = APIRouter()


@router.get("/kline", response_model=KLineResponse)
def get_kline(
    symbol: str = Query(..., min_length=1, examples=["RB0909"]),
    offset: int | None = Query(None, ge=0),
    limit: int = Query(2000),
) -> KLineResponse:
    """业务功能: 返回单个合约的一页标准 OHLCV K 线数据。"""
    try:
        safe_limit = normalize_limit(limit)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return get_kline_reader().load(symbol=symbol, offset=offset, limit=safe_limit)
