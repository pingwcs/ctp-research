"""
Aggregation module: 5-minute resampling, MA indicators, and daily volume stats.
"""
import pandas as pd
import numpy as np
from typing import Optional


def resample_to_5min(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resample 1-minute data to 5-minute bars.

    Rules:
      - open/close: first/last in window
      - high/low: max/min in window
      - amount/volume: sum in window
      - position: last in window
      - bob: window start (from index)
      - eob: window end (last eob in window)
      - exchange/symbol: preserved
    """
    if df.empty:
        return df

    df = df.copy()
    if "bob" not in df.columns:
        raise ValueError("DataFrame must have 'bob' column for resampling")

    # Ensure bob is datetime and set as index for resample
    df["_bob_idx"] = pd.to_datetime(df["bob"], utc=True)
    df = df.set_index("_bob_idx")

    # Build aggregation rules for every column except the index (bob)
    agg_rules = {}
    for col in df.columns:
        if col == "bob":
            continue  # bob becomes the index; omit from aggregation
        if col in ("open",):
            agg_rules[col] = "first"
        elif col in ("close",):
            agg_rules[col] = "last"
        elif col in ("high",):
            agg_rules[col] = "max"
        elif col in ("low",):
            agg_rules[col] = "min"
        elif col in ("amount", "volume"):
            agg_rules[col] = "sum"
        elif col in ("position",):
            agg_rules[col] = "last"
        elif col in ("exchange", "symbol", "eob"):
            agg_rules[col] = "last"
        else:
            agg_rules[col] = "first"

    available_cols = {c: agg_rules[c] for c in agg_rules if c in df.columns}

    resampled = df.resample("5min").agg(available_cols)

    # Drop rows where all key numeric fields are NaN (empty windows)
    key_fields = [c for c in ["open", "close", "high", "low"] if c in resampled.columns]
    if key_fields:
        resampled = resampled.dropna(subset=key_fields, how="all")

    # Reset index: the DatetimeIndex becomes a column named 'bob'
    resampled = resampled.reset_index(drop=False)
    if "_bob_idx" in resampled.columns:
        resampled = resampled.rename(columns={"_bob_idx": "bob"})

    return resampled


def calculate_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """Add ma5 and ma20 columns based on 5-minute close prices."""
    if "close" not in df.columns:
        return df

    df = df.copy()
    df["ma5"] = df["close"].rolling(window=5, min_periods=1).mean()
    df["ma20"] = df["close"].rolling(window=20, min_periods=1).mean()
    return df


def compute_daily_volume(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute daily cumulative volume per contract.
    Returns DataFrame with columns: symbol, date, daily_volume.
    """
    if df.empty or "volume" not in df.columns or "bob" not in df.columns:
        return pd.DataFrame(columns=["symbol", "date", "daily_volume"])

    df = df.copy()
    df["date"] = pd.to_datetime(df["bob"], utc=True).dt.date
    daily = df.groupby(["symbol", "date"], as_index=False)["volume"].sum()
    daily = daily.rename(columns={"volume": "daily_volume"})
    return daily


def compute_daily_volume_summary(contract_dailies: list[pd.DataFrame]) -> pd.DataFrame:
    """
    Combine daily volumes from all contracts and compute is_max_daily_volume flag.

    is_max_daily_volume is True for the contract with the highest daily_volume
    on each date across all contracts.
    """
    if not contract_dailies:
        return pd.DataFrame(columns=["symbol", "date", "daily_volume", "is_max_daily_volume"])

    combined = pd.concat(contract_dailies, ignore_index=True)
    if combined.empty:
        return combined

    # Aggregate again in case the same symbol appears from different files
    combined = combined.groupby(["symbol", "date"], as_index=False)["daily_volume"].sum()

    # Find max daily volume per date
    max_per_date = combined.groupby("date")["daily_volume"].transform("max")
    combined["is_max_daily_volume"] = combined["daily_volume"] == max_per_date

    return combined
