"""Market-data response schemas.

业务功能: 定义前端 K 线图使用的行情 HTTP 响应结构。
算法要点: 时间统一为 Unix 秒，价格和成交量统一为 float，前端不用关心
parquet 源字段命名。
"""

from pydantic import BaseModel, Field


class Candle(BaseModel):
    """业务功能: 一根标准 OHLCV 蜡烛。"""

    time: int = Field(..., description="Unix timestamp in seconds")
    open: float
    high: float
    low: float
    close: float
    volume: float


class KLineResponse(BaseModel):
    """业务功能: 带分页信息的一组合约 K 线数据。"""

    symbol: str
    total: int = Field(
        ...,
        description="Total candles available for the symbol",
    )
    offset: int = Field(
        ...,
        description="Zero-based offset of this response window",
    )
    limit: int = Field(..., description="Maximum candle count requested")
    candles: list[Candle]
