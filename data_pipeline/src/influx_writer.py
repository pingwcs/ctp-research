"""
InfluxDB write module for the futures data pipeline.

Writes 5-minute bar data to InfluxDB using the official influxdb-client library.
Supports SYNCHRONOUS write mode with configurable batch size and retry on failure.
"""
import logging
import time
from typing import Optional

import pandas as pd
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError

from src.config import InfluxDBConfig

logger = logging.getLogger(__name__)

# Maximum retries for transient failures
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


def _build_point(row, measurement: str, tag_columns: list[str], field_columns: list[str]):
    """Build a single InfluxDB Point from a DataFrame row."""
    from influxdb_client import Point

    point = Point(measurement)

    # Tags
    for tag in tag_columns:
        if tag in row.index and not pd.isna(row[tag]):
            point = point.tag(tag, str(row[tag]))

    # Timestamp: bob must be in UTC, convert to nanoseconds
    ts = row["bob"]
    if isinstance(ts, pd.Timestamp):
        point = point.time(ts, write_precision="ns")

    # Fields
    for field in field_columns:
        if field in row.index and not pd.isna(row[field]):
            val = row[field]
            point = point.field(field, float(val))

    return point


def save_to_influxdb(df: pd.DataFrame, config: InfluxDBConfig) -> int:
    """
    Write a DataFrame of 5-minute bars to InfluxDB.

    Returns the number of points successfully written.

    The DataFrame must contain: bob (timestamp), symbol, exchange, and numeric fields.
    """
    if not config.enabled:
        logger.info("InfluxDB writing disabled by config. Skipping.")
        return 0

    if df.empty:
        logger.info("Empty DataFrame, nothing to write to InfluxDB.")
        return 0

    tag_columns = ["symbol", "exchange"]
    field_columns = ["open", "close", "high", "low", "amount", "volume", "position", "ma5", "ma20"]
    timestamp_col = "bob"

    if timestamp_col not in df.columns:
        raise ValueError(f"DataFrame must contain '{timestamp_col}' column for InfluxDB timestamp")

    # Ensure bob is timezone-aware UTC
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df[timestamp_col]):
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True)
    if df[timestamp_col].dt.tz is None:
        df[timestamp_col] = df[timestamp_col].dt.tz_localize("UTC")
    else:
        df[timestamp_col] = df[timestamp_col].dt.tz_convert("UTC")

    # Drop rows where bob is NaT
    df = df.dropna(subset=[timestamp_col])

    client: Optional[InfluxDBClient] = None
    points_written = 0

    try:
        client = InfluxDBClient(url=config.url, token=config.token, org=config.org,
                                timeout=config.write_timeout_ms)
        write_api = client.write_api(write_options=SYNCHRONOUS)

        # Build points in batches
        batch = []
        for _, row in df.iterrows():
            point = _build_point(row, config.measurement, tag_columns, field_columns)
            batch.append(point)

            if len(batch) >= config.batch_size:
                points_written += _write_batch_with_retry(write_api, batch, config)
                batch = []

        # Flush remaining
        if batch:
            points_written += _write_batch_with_retry(write_api, batch, config)

        logger.info(f"Successfully wrote {points_written} points to InfluxDB measurement '{config.measurement}'")

    except InfluxDBError as e:
        logger.error(f"InfluxDB error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error writing to InfluxDB: {e}")
    finally:
        if client is not None:
            client.close()

    return points_written


def _write_batch_with_retry(write_api, batch: list, config: InfluxDBConfig) -> int:
    """Write a batch of points with retry logic for transient failures."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            write_api.write(bucket=config.bucket, org=config.org, record=batch)
            return len(batch)
        except InfluxDBError as e:
            logger.warning(f"InfluxDB write attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
            else:
                logger.error(f"InfluxDB write failed after {MAX_RETRIES} attempts")
                raise
    return 0
