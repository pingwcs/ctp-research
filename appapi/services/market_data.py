"""Read and normalize OHLCV data from contract parquet files.

业务功能: 为行情接口读取本地 5 分钟合约 parquet，并输出前端图表需要的
标准 OHLCV 窗口。
算法要点: 用 DuckDB 原地扫描 parquet，只选择非空 OHLC 字段，按时间
排序后通过 LIMIT/OFFSET 做窗口分页，避免一次把大文件全部读入 Python。
"""

from pathlib import Path

import duckdb
from fastapi import HTTPException, status
from loguru import logger

from appapi.schemas.market import KLineResponse
from appapi.services.parquet_utils import (
    column_map,
    describe_columns,
    parquet_path_literal,
    quote_identifier,
    resolve_contract_file,
)


def _build_select_sql(
    parquet_path: Path,
    mapped: dict[str, str],
    offset: int,
    limit: int,
) -> str:
    """算法要点: 构造标准 OHLCV 投影 SQL，并把时间转成 Unix 秒。"""
    time_column = quote_identifier(mapped["time"])
    return f"""
        SELECT
            epoch(CAST({time_column} AS TIMESTAMP))::BIGINT AS time,
            CAST({quote_identifier(mapped["open"])} AS DOUBLE) AS open,
            CAST({quote_identifier(mapped["high"])} AS DOUBLE) AS high,
            CAST({quote_identifier(mapped["low"])} AS DOUBLE) AS low,
            CAST({quote_identifier(mapped["close"])} AS DOUBLE) AS close,
            CAST({quote_identifier(mapped["volume"])} AS DOUBLE) AS volume
        FROM read_parquet('{parquet_path_literal(parquet_path)}')
        WHERE {time_column} IS NOT NULL
          AND {quote_identifier(mapped["open"])} IS NOT NULL
          AND {quote_identifier(mapped["high"])} IS NOT NULL
          AND {quote_identifier(mapped["low"])} IS NOT NULL
          AND {quote_identifier(mapped["close"])} IS NOT NULL
        ORDER BY {time_column}
        LIMIT {int(limit)} OFFSET {int(offset)}
    """


def _build_count_sql(parquet_path: Path, mapped: dict[str, str]) -> str:
    """算法要点: 统计可绘制蜡烛数量，过滤规则和查询窗口保持一致。"""
    time_column = quote_identifier(mapped["time"])
    return f"""
        SELECT COUNT(*)::BIGINT
        FROM read_parquet('{parquet_path_literal(parquet_path)}')
        WHERE {time_column} IS NOT NULL
          AND {quote_identifier(mapped["open"])} IS NOT NULL
          AND {quote_identifier(mapped["high"])} IS NOT NULL
          AND {quote_identifier(mapped["low"])} IS NOT NULL
          AND {quote_identifier(mapped["close"])} IS NOT NULL
    """


def load_kline_data(
    symbol: str,
    offset: int | None = None,
    limit: int = 2000,
) -> KLineResponse:
    """业务功能: 读取指定合约的一页 K 线数据并返回图表 DTO。

    算法要点: 未指定 offset 时默认取最新窗口；指定 offset 时限制在
    合法范围内，保证返回窗口不会越过有效数据边界。
    """
    parquet_path = resolve_contract_file(symbol)
    safe_limit = max(1, min(limit, 2000))
    logger.info(
        "Loading kline data: symbol={}, file={}, offset={}, limit={}",
        symbol,
        parquet_path,
        offset,
        safe_limit,
    )

    try:
        with duckdb.connect(
            database=":memory:",
            read_only=False,
        ) as connection:
            columns = describe_columns(connection, parquet_path)
            mapped = column_map(columns)
            total = int(
                connection.execute(
                    _build_count_sql(parquet_path, mapped),
                ).fetchone()[0]
            )
            if offset is None:
                safe_offset = max(0, total - safe_limit)
            else:
                safe_offset = max(0, offset)
            if total:
                safe_offset = min(safe_offset, max(0, total - 1))
            rows = connection.execute(
                _build_select_sql(
                    parquet_path,
                    mapped,
                    safe_offset,
                    safe_limit,
                ),
            ).fetchall()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Failed to load parquet data: symbol={}, file={}",
            symbol,
            parquet_path,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"failed to read market data for {symbol}: {exc}",
        ) from exc

    candles = []
    for time_value, open_, high, low, close, volume in rows:
        candle = {
            "time": int(time_value),
            "open": float(open_),
            "high": float(high),
            "low": float(low),
            "close": float(close),
            "volume": float(volume),
        }
        candles.append(candle)

    logger.info(
        "Loaded {} candles for {}",
        len(candles),
        symbol,
    )
    return KLineResponse(
        symbol=symbol,
        total=total,
        offset=safe_offset,
        limit=safe_limit,
        candles=candles,
    )
