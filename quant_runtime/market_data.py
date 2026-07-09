"""Canonical 1-minute parquet market data for the quant runtime."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

import pandas as pd

from quant_runtime.settings import settings


REQUIRED_COLUMNS = {
    "exchange",
    "symbol",
    "eob",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "position",
}
SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class NormalizedBar:
    exchange: str
    symbol: str
    datetime: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    turnover: float
    open_interest: float


class MarketDataError(Exception):
    """Raised when canonical parquet market data cannot be read."""


def _symbol_parquet_path(symbol: str, data_dir: Path) -> Path:
    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise MarketDataError(
            "symbol may only contain letters, numbers, underscore, dash and dot",
        )

    root = data_dir.resolve()
    path = (root / f"{symbol}.parquet").resolve()
    if root not in path.parents:
        raise MarketDataError("invalid symbol path")
    if not path.exists():
        raise MarketDataError(f"contract parquet not found: data/output/1min/{symbol}.parquet")
    return path


def _parse_datetime(value) -> datetime:
    timestamp = pd.to_datetime(value)
    if isinstance(timestamp, pd.Timestamp):
        return timestamp.to_pydatetime()
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _in_range(
    value: datetime,
    start_time: datetime | None,
    end_time: datetime | None,
) -> bool:
    if start_time is not None and value < start_time:
        return False
    if end_time is not None and value > end_time:
        return False
    return True


def list_symbols(data_dir: Path = settings.minute_data_dir) -> list[str]:
    if not data_dir.exists():
        return []
    return sorted(path.stem for path in data_dir.glob("*.parquet") if path.is_file())


def read_minute_bars(
    symbol: str,
    data_dir: Path = settings.minute_data_dir,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[NormalizedBar]:
    path = _symbol_parquet_path(symbol, data_dir)
    frame = pd.read_parquet(path)
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise MarketDataError(
            "parquet missing required columns: "
            + ", ".join(missing)
            + "; available columns: "
            + ", ".join(frame.columns),
        )

    bars: list[NormalizedBar] = []
    for row in frame.to_dict("records"):
        bar_time = _parse_datetime(row["eob"])
        if row["symbol"] != symbol or not _in_range(bar_time, start_time, end_time):
            continue
        bars.append(
            NormalizedBar(
                exchange=str(row["exchange"]),
                symbol=str(row["symbol"]),
                datetime=bar_time,
                open_price=float(row["open"]),
                high_price=float(row["high"]),
                low_price=float(row["low"]),
                close_price=float(row["close"]),
                volume=float(row["volume"]),
                turnover=float(row["amount"]),
                open_interest=float(row["position"]),
            ),
        )
    return bars
