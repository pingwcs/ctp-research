"""Deep module for reading K-line windows from parquet files."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, ContextManager

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


class KLineReader:
    """Read normalized OHLCV windows from contract parquet files."""

    def __init__(
        self,
        connection_factory: Callable[[], ContextManager] | None = None,
        contract_resolver: Callable[[str], Path] = resolve_contract_file,
    ) -> None:
        self._connection_factory = connection_factory or _duckdb_memory_connection
        self._contract_resolver = contract_resolver

    def load(
        self,
        symbol: str,
        offset: int | None = None,
        limit: int = 2000,
    ) -> KLineResponse:
        parquet_path = self._contract_resolver(symbol)
        safe_limit = _safe_limit(limit)
        logger.info(
            "Loading kline data: symbol={}, file={}, offset={}, limit={}",
            symbol,
            parquet_path,
            offset,
            safe_limit,
        )

        try:
            with self._connection_factory() as connection:
                columns = describe_columns(connection, parquet_path)
                mapped = column_map(columns)
                total = int(
                    connection.execute(
                        _build_count_sql(parquet_path, mapped),
                    ).fetchone()[0]
                )
                safe_offset = _safe_offset(total, safe_limit, offset)
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

        logger.info("Loaded {} candles for {}", len(rows), symbol)
        return KLineResponse(
            symbol=symbol,
            total=total,
            offset=safe_offset,
            limit=safe_limit,
            candles=[_row_to_candle(row) for row in rows],
        )


_kline_reader: KLineReader | None = None


def get_kline_reader() -> KLineReader:
    global _kline_reader
    if _kline_reader is None:
        _kline_reader = KLineReader()
    return _kline_reader


def load_kline_data(
    symbol: str,
    offset: int | None = None,
    limit: int = 2000,
) -> KLineResponse:
    return get_kline_reader().load(symbol=symbol, offset=offset, limit=limit)


def _duckdb_memory_connection():
    return duckdb.connect(database=":memory:", read_only=False)


def _safe_limit(limit: int) -> int:
    return max(1, min(limit, 2000))


def _safe_offset(total: int, limit: int, offset: int | None) -> int:
    if offset is None:
        return max(0, total - limit)

    safe_offset = max(0, offset)
    if total:
        safe_offset = min(safe_offset, max(0, total - 1))
    return safe_offset


def _build_select_sql(
    parquet_path: Path,
    mapped: dict[str, str],
    offset: int,
    limit: int,
) -> str:
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


def _row_to_candle(row) -> dict[str, float | int]:
    time_value, open_, high, low, close, volume = row
    return {
        "time": int(time_value),
        "open": float(open_),
        "high": float(high),
        "low": float(low),
        "close": float(close),
        "volume": float(volume),
    }
