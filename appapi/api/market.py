"""Market-data HTTP endpoints.

业务功能: 暴露 K 线查询 API，让前端按合约、偏移和窗口大小读取本地
parquet 行情。
算法要点: HTTP 层只声明参数约束，分页、字段识别和数据归一化由
services.market_data 处理。
"""

from fastapi import APIRouter, Query

from appapi.schemas.market import KLineResponse
from appapi.services.market_data import load_kline_data


router = APIRouter()


@router.get("/kline", response_model=KLineResponse)
def get_kline(
    symbol: str = Query(..., min_length=1, examples=["RB0909"]),
    offset: int | None = Query(None, ge=0),
    limit: int = Query(2000, ge=1, le=2000),
) -> KLineResponse:
    """业务功能: 返回单个合约的一页标准 OHLCV K 线数据。"""
    return load_kline_data(symbol=symbol, offset=offset, limit=limit)
