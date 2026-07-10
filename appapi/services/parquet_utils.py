"""Shared helpers for reading local contract parquet files.

业务功能: 集中处理行情 parquet 的路径解析、SQL 转义和字段名兼容。
算法要点: 先校验 symbol 字符集，再用 resolve 后的父目录检查防止路径
穿越；字段映射采用大小写无关别名表，屏蔽不同数据源的列名差异。
"""

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
    """业务功能: 把合约代码解析成 data/output/5min 下的 parquet 文件。

    算法要点: symbol 只能包含安全字符，最终路径必须仍位于 5min 根目录。
    """
    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "symbol may only contain letters, numbers, underscore, "
                "dash and dot"
            ),
        )

    data_dir = (settings.data_dir / "5min").resolve()
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
                f"../data/output/5min/{symbol}.parquet"
            ),
        )
    return path


def quote_identifier(name: str) -> str:
    """算法要点: 按 DuckDB 标识符规则转义列名中的双引号。"""
    return '"' + name.replace('"', '""') + '"'


def parquet_path_literal(parquet_path: Path) -> str:
    """算法要点: 按 SQL 字符串规则转义 parquet 路径中的单引号。"""
    return str(parquet_path).replace("'", "''")


def column_map(columns: list[str]) -> dict[str, str]:
    """业务功能: 将源 parquet 列名映射成统一的 time/open/high/low/close/volume。

    算法要点: 使用小写索引匹配 bob/eob、OHLC 缩写等别名，缺少必要字段时
    返回 422，提示调用方当前文件不可作为 K 线数据源。
    """
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
    """业务功能: 读取 parquet schema 中的列名供字段映射使用。"""
    rows = connection.execute(
        "DESCRIBE SELECT * FROM read_parquet(?)",
        [str(parquet_path)],
    ).fetchall()
    return [row[0] for row in rows]
