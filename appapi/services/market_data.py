"""Read and normalize OHLCV data from contract parquet files."""

from pathlib import Path
import re

import duckdb
from fastapi import HTTPException, status
from loguru import logger

from appapi.core.config import settings
from appapi.schemas.market import KLineResponse, TradeMarker


SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")

# The local parquet files use bob/eob. Prefer eob because a 5-minute bar is
# usually plotted at its closing timestamp.
TIME_COLUMNS = ("eob", "bob", "datetime", "timestamp", "time", "date")
FIELD_ALIASES = {
    "open": ("open", "o"),
    "high": ("high", "h"),
    "low": ("low", "l"),
    "close": ("close", "c"),
    "volume": ("volume", "vol", "qty"),
    "signal": ("signal", "trade_signal", "signals"),
}


def _resolve_contract_file(symbol: str) -> Path:
    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="symbol may only contain letters, numbers, underscore, dash and dot",
        )

    data_dir = settings.data_dir.resolve()
    path = (data_dir / f"{symbol}.parquet").resolve()
    if data_dir not in path.parents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid symbol path",
        )
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"contract parquet not found: ../data/output/{symbol}.parquet",
        )
    return path


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _column_map(columns: list[str]) -> dict[str, str]:
    by_lower = {column.lower(): column for column in columns}

    mapped: dict[str, str] = {}
    for candidate in TIME_COLUMNS:
        if candidate in by_lower:
            mapped["time"] = by_lower[candidate]
            break

    for normalized, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in by_lower:
                mapped[normalized] = by_lower[alias]
                break

    required = ("time", "open", "high", "low", "close", "volume")
    missing = [name for name in required if name not in mapped]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "parquet missing required columns: "
                f"{', '.join(missing)}; available columns: {', '.join(columns)}"
            ),
        )
    return mapped


def _describe_columns(connection: duckdb.DuckDBPyConnection, parquet_path: Path) -> list[str]:
    rows = connection.execute(
        "DESCRIBE SELECT * FROM read_parquet(?)",
        [str(parquet_path)],
    ).fetchall()
    return [row[0] for row in rows]


def _build_select_sql(parquet_path: Path, mapped: dict[str, str]) -> str:
    time_column = _quote_identifier(mapped["time"])
    signal_expr = "NULL AS signal"
    if "signal" in mapped:
        signal_expr = f"CAST({_quote_identifier(mapped['signal'])} AS VARCHAR) AS signal"

    return f"""
        SELECT
            epoch(CAST({time_column} AS TIMESTAMP))::BIGINT AS time,
            CAST({_quote_identifier(mapped["open"])} AS DOUBLE) AS open,
            CAST({_quote_identifier(mapped["high"])} AS DOUBLE) AS high,
            CAST({_quote_identifier(mapped["low"])} AS DOUBLE) AS low,
            CAST({_quote_identifier(mapped["close"])} AS DOUBLE) AS close,
            CAST({_quote_identifier(mapped["volume"])} AS DOUBLE) AS volume,
            {signal_expr}
        FROM read_parquet('{str(parquet_path).replace("'", "''")}')
        WHERE {time_column} IS NOT NULL
          AND {_quote_identifier(mapped["open"])} IS NOT NULL
          AND {_quote_identifier(mapped["high"])} IS NOT NULL
          AND {_quote_identifier(mapped["low"])} IS NOT NULL
          AND {_quote_identifier(mapped["close"])} IS NOT NULL
        ORDER BY {time_column}
    """


def _marker_from_signal(time_value: int, signal: str | None) -> TradeMarker | None:
    if not signal:
        return None
    normalized = signal.strip().lower()
    if normalized == "buy":
        return TradeMarker(
            time=time_value,
            position="belowBar",
            color="#16a34a",
            shape="arrowUp",
            text="Buy",
        )
    if normalized == "sell":
        return TradeMarker(
            time=time_value,
            position="aboveBar",
            color="#dc2626",
            shape="arrowDown",
            text="Sell",
        )
    return None


def load_kline_data(symbol: str) -> KLineResponse:
    parquet_path = _resolve_contract_file(symbol)
    logger.info("Loading kline data: symbol={}, file={}", symbol, parquet_path)

    try:
        with duckdb.connect(database=":memory:", read_only=False) as connection:
            columns = _describe_columns(connection, parquet_path)
            mapped = _column_map(columns)
            rows = connection.execute(_build_select_sql(parquet_path, mapped)).fetchall()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to load parquet data: symbol={}, file={}", symbol, parquet_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"failed to read market data for {symbol}: {exc}",
        ) from exc

    candles = []
    markers = []
    for time_value, open_, high, low, close, volume, signal in rows:
        candle = {
            "time": int(time_value),
            "open": float(open_),
            "high": float(high),
            "low": float(low),
            "close": float(close),
            "volume": float(volume),
        }
        candles.append(candle)

        marker = _marker_from_signal(int(time_value), signal)
        if marker:
            markers.append(marker)

    logger.info("Loaded {} candles and {} markers for {}", len(candles), len(markers), symbol)
    return KLineResponse(symbol=symbol, candles=candles, markers=markers)
