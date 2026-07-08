"""Load normalized backtest rows from local parquet files."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
from fastapi import HTTPException, status
from loguru import logger

from appapi.schemas.backtest import BacktestRunRequest
from appapi.services.backtest.types import BacktestBar
from appapi.services.parquet_utils import (
    column_map,
    describe_columns,
    parquet_path_literal,
    quote_identifier,
    resolve_contract_file,
)


DATA_TIMEZONE = ZoneInfo("Asia/Shanghai")


def _to_epoch(value: datetime | None) -> int | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=DATA_TIMEZONE)
    return int(value.timestamp())


def _optional_double_expr(mapped: dict[str, str], key: str) -> str:
    if key not in mapped:
        return "NULL"
    return f"CAST({quote_identifier(mapped[key])} AS DOUBLE)"


def _build_backtest_sql(
    parquet_path: Path,
    mapped: dict[str, str],
    start_epoch: int | None,
    end_epoch: int | None,
) -> str:
    time_column = quote_identifier(mapped["time"])
    time_epoch_expr = f"epoch({time_column})"
    close_column = quote_identifier(mapped["close"])
    where_clauses = [
        f"{time_column} IS NOT NULL",
        f"{close_column} IS NOT NULL",
    ]
    if start_epoch is not None:
        where_clauses.append(f"{time_epoch_expr} >= {start_epoch}")
    if end_epoch is not None:
        where_clauses.append(f"{time_epoch_expr} <= {end_epoch}")

    return f"""
        SELECT
            {time_epoch_expr}::BIGINT AS time,
            CAST({close_column} AS DOUBLE) AS close,
            AVG(CAST({close_column} AS DOUBLE)) OVER (
                ORDER BY {time_column} ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ) AS fallback_ma5,
            AVG(CAST({close_column} AS DOUBLE)) OVER (
                ORDER BY {time_column}
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) AS fallback_ma20,
            {_optional_double_expr(mapped, "ma5")} AS file_ma5,
            {_optional_double_expr(mapped, "ma20")} AS file_ma20
        FROM read_parquet('{parquet_path_literal(parquet_path)}')
        WHERE {" AND ".join(where_clauses)}
        ORDER BY {time_column}
    """


def _extend_indicator_columns(
    columns: list[str],
    mapped: dict[str, str],
) -> dict[str, str]:
    by_lower = {column.lower(): column for column in columns}
    extended = dict(mapped)
    if "ma5" in by_lower:
        extended["ma5"] = by_lower["ma5"]
    if "ma20" in by_lower:
        extended["ma20"] = by_lower["ma20"]
    return extended


def load_rows(request: BacktestRunRequest) -> list[BacktestBar]:
    parquet_path = resolve_contract_file(request.symbol)
    start_epoch = _to_epoch(request.start_time)
    end_epoch = _to_epoch(request.end_time)
    if start_epoch is not None and end_epoch is not None and start_epoch > end_epoch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be before end_time",
        )

    try:
        with duckdb.connect(
            database=":memory:",
            read_only=False,
        ) as connection:
            columns = describe_columns(connection, parquet_path)
            mapped = _extend_indicator_columns(columns, column_map(columns))
            rows = connection.execute(
                _build_backtest_sql(
                    parquet_path,
                    mapped,
                    start_epoch,
                    end_epoch,
                ),
            ).fetchall()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to load backtest rows for {}", request.symbol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"failed to load backtest data: {exc}",
        ) from exc

    normalized = []
    for row in rows:
        (
            time_value,
            close,
            fallback_ma5,
            fallback_ma20,
            file_ma5,
            file_ma20,
        ) = row
        ma5 = float(file_ma5 if file_ma5 is not None else fallback_ma5)
        ma20 = float(file_ma20 if file_ma20 is not None else fallback_ma20)
        normalized.append(
            BacktestBar(
                time=int(time_value),
                close=float(close),
                ma5=ma5,
                ma20=ma20,
            ),
        )
    return normalized
