"""Hive-style partition locations for historical market data."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class MarketPartition:
    source: str
    exchange: str
    instrument: str
    trading_date: date


def partition_path(root: str | Path, partition: MarketPartition) -> Path:
    """Return the canonical Parquet file path for a market-data partition."""
    return (
        Path(root)
        / f"source={partition.source}"
        / f"exchange={partition.exchange}"
        / f"instrument={partition.instrument}"
        / f"trading_date={partition.trading_date.isoformat()}"
        / "ticks.parquet"
    )
