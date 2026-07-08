"""Shared helpers for reading local contract parquet files."""

from pathlib import Path
import re

import duckdb
from fastapi import HTTPException, status

from appapi.core.config import settings


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


def resolve_contract_file(symbol: str) -> Path:
    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "symbol may only contain letters, numbers, underscore, "
                "dash and dot"
            ),
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
            detail=(
                "contract parquet not found: "
                f"../data/output/{symbol}.parquet"
            ),
        )
    return path


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def parquet_path_literal(parquet_path: Path) -> str:
    return str(parquet_path).replace("'", "''")


def column_map(columns: list[str]) -> dict[str, str]:
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
                f"{', '.join(missing)}; "
                f"available columns: {', '.join(columns)}"
            ),
        )
    return mapped


def describe_columns(
    connection: duckdb.DuckDBPyConnection,
    parquet_path: Path,
) -> list[str]:
    rows = connection.execute(
        "DESCRIBE SELECT * FROM read_parquet(?)",
        [str(parquet_path)],
    ).fetchall()
    return [row[0] for row in rows]
