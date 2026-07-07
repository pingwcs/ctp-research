"""
Data cleaning module for futures contract minute-level data.

Handles:
  - Timestamp rounding to nearest minute
  - Missing value forward/backward fill (excluding 'type' column)
  - Duplicate (bob, eob) key merging with numeric averaging

Each function returns (cleaned_df, list[AnomalyRecord]).
"""
import pandas as pd
import numpy as np
from typing import Optional

from src.logger import AnomalyRecord

# Columns that are numeric and subject to cleaning/value-fill logic
NUMERIC_COLS = ["open", "close", "high", "low", "amount", "volume", "position"]
NON_NUMERIC_COLS = ["exchange", "symbol"]
DROP_COLS = ["type"]


def _round_to_nearest_minute(ts: pd.Timestamp) -> pd.Timestamp:
    """Round timestamp to nearest minute. seconds >= 30 rounds up, < 30 rounds down."""
    if pd.isna(ts):
        return ts
    if ts.second >= 30:
        return ts.ceil("min")
    return ts.floor("min")


def clean_timestamps(df: pd.DataFrame, file_name: str, symbol: str) -> tuple[pd.DataFrame, list[AnomalyRecord]]:
    """Check and round bob/eob timestamps to nearest minute, logging corrections."""
    anomalies: list[AnomalyRecord] = []

    for col in ["bob", "eob"]:
        if col not in df.columns:
            continue
        # Convert to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col], utc=True)

        for idx in df.index:
            original = df.at[idx, col]
            if pd.isna(original):
                continue
            rounded = _round_to_nearest_minute(original)
            if rounded != original:
                anomalies.append(AnomalyRecord(
                    file_name=file_name, symbol=symbol, row_index=int(idx),
                    field=col,
                    original_value=str(original), corrected_value=str(rounded),
                    anomaly_type="timestamp_rounding",
                ))
                df.at[idx, col] = rounded

    return df, anomalies


def fill_missing_values(df: pd.DataFrame, file_name: str, symbol: str) -> tuple[pd.DataFrame, list[AnomalyRecord]]:
    """
    Fill missing values in numeric columns (excluding 'type').
    Priority: forward fill, then backward fill for any remaining NaN at the start.
    """
    anomalies: list[AnomalyRecord] = []
    fill_cols = [c for c in NUMERIC_COLS if c in df.columns]

    for col in fill_cols:
        for idx in df.index:
            if pd.isna(df.at[idx, col]):
                # Try forward fill
                ffill_val = df[col].iloc[:idx].dropna()
                if len(ffill_val) > 0:
                    fill_val = ffill_val.iloc[-1]
                    fill_source = "前值"
                else:
                    # Try backward fill
                    bfill_val = df[col].iloc[idx + 1:].dropna()
                    if len(bfill_val) > 0:
                        fill_val = bfill_val.iloc[0]
                        fill_source = "后值"
                    else:
                        continue  # Can't fill, skip

                anomalies.append(AnomalyRecord(
                    file_name=file_name, symbol=symbol, row_index=int(idx),
                    field=col,
                    original_value="NaN", corrected_value=str(fill_val),
                    anomaly_type="missing_value_filled",
                    detail=fill_source,
                ))
                df.at[idx, col] = fill_val

    return df, anomalies


def deduplicate_rows(df: pd.DataFrame, file_name: str, symbol: str) -> tuple[pd.DataFrame, list[AnomalyRecord]]:
    """
    Detect duplicate (bob, eob) rows. For duplicates:
      - Numeric fields: average
      - Non-numeric fields: keep first
    Log each merge event.
    """
    anomalies: list[AnomalyRecord] = []

    key_cols = [c for c in ["bob", "eob"] if c in df.columns]
    if not key_cols:
        return df, anomalies

    # Ensure key columns are comparable (convert to string representation for grouping
    # if they contain mixed datetime/tuple types from prior edge cases)
    dup_mask = df.duplicated(subset=key_cols, keep=False)
    if not dup_mask.any():
        return df, anomalies

    dup_groups = df[dup_mask].groupby(key_cols, dropna=False)

    rows_to_drop: list[int] = []
    merged_rows: list[dict] = []

    for keys, group in dup_groups:
        row_indices = list(group.index)
        if len(row_indices) < 2:
            continue

        merged = {}
        # Numeric: average
        for col in [c for c in NUMERIC_COLS if c in df.columns]:
            vals = group[col].dropna()
            merged[col] = vals.mean() if len(vals) > 0 else np.nan
        # Non-numeric: first valid
        for col in [c for c in NON_NUMERIC_COLS if c in df.columns]:
            valid = group[col].dropna()
            merged[col] = valid.iloc[0] if len(valid) > 0 else group[col].iloc[0]

        # Key columns: unpack properly so each gets its own value
        if isinstance(keys, tuple):
            for i, col in enumerate(key_cols):
                merged[col] = keys[i]
        else:
            merged[key_cols[0]] = keys

        merged_rows.append(merged)
        rows_to_drop.extend(row_indices)

        anomalies.append(AnomalyRecord(
            file_name=file_name, symbol=symbol,
            row_index=row_indices[0],
            field="bob+eob",
            original_value=str(keys), corrected_value="merged",
            anomaly_type="duplicate_merged",
            detail=f"row_indices={row_indices}",
        ))

    df_clean = df.drop(index=rows_to_drop)
    if merged_rows:
        df_merged = pd.DataFrame(merged_rows)
        df_clean = pd.concat([df_clean, df_merged], ignore_index=True)

    return df_clean, anomalies
def clean_dataframe(df: pd.DataFrame, file_name: str, symbol: str) -> tuple[pd.DataFrame, list[AnomalyRecord]]:
    """Run the full cleaning pipeline on a single contract DataFrame."""
    all_anomalies: list[AnomalyRecord] = []

    # 1. Drop 'type' column if present
    for col in DROP_COLS:
        if col in df.columns:
            df = df.drop(columns=[col])

    # 2. Timestamp rounding
    df, anomalies = clean_timestamps(df, file_name, symbol)
    all_anomalies.extend(anomalies)

    # 3. Missing value fill
    df, anomalies = fill_missing_values(df, file_name, symbol)
    all_anomalies.extend(anomalies)

    # 4. Deduplication
    df, anomalies = deduplicate_rows(df, file_name, symbol)
    all_anomalies.extend(anomalies)

    # Sort by bob
    if "bob" in df.columns:
        df = df.sort_values("bob").reset_index(drop=True)

    return df, all_anomalies
