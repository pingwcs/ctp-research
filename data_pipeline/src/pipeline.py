"""
Main pipeline orchestrator.

Coordinates:
  - Multi-process CSV file processing via ProcessPoolExecutor
  - Per-contract: read -> clean -> export 1min -> resample 5min -> MA -> export Parquet -> InfluxDB
  - Cross-process log collection
  - Daily volume summary assembly
"""

import os
import logging
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Optional

import pandas as pd
import pyarrow as pa

from market_data import MarketPartition, partition_path, publish_parquet
from src.config import PipelineConfig, config as default_config
from src.logger import AnomalyRecord, collect_worker_logs, write_quality_log
from src.cleaner import clean_dataframe
from src.aggregator import (
    resample_to_5min,
    calculate_moving_averages,
    compute_daily_volume,
    compute_daily_volume_summary,
)
from src.influx_writer import save_to_influxdb

logger = logging.getLogger(__name__)


def _extract_symbol(file_path: str) -> str:
    """Extract contract symbol from filename, e.g. 'RB0909.csv' -> 'RB0909'."""
    base = os.path.basename(file_path)
    return os.path.splitext(base)[0]


def process_single_contract(
    csv_path: str,
    output_dir: str,
    influx_config,
    minute_output_subdir: str | None = None,
    kline_output_subdir: str | None = None,
    market_root: str | None = None,
) -> dict:
    """
    Process a single contract CSV end-to-end. Designed to run in a worker process.

    Returns a dict with:
      - anomalies: list[AnomalyRecord]
      - daily_volume_df: DataFrame (symbol, date, daily_volume) or None
      - parquet_path: str or None
      - points_written: int
      - error: str or None
    """
    file_name = os.path.basename(csv_path)
    symbol = _extract_symbol(csv_path)
    result = {
        "anomalies": [],
        "daily_volume_df": None,
        "parquet_path": None,
        "minute_parquet_path": None,
        "points_written": 0,
        "error": None,
    }

    try:
        # 1. Read CSV
        df = pd.read_csv(csv_path)
        if df.empty:
            logger.warning(f"[{symbol}] Empty CSV, skipping.")
            return result

        # 2. Clean
        df, anomalies = clean_dataframe(df, file_name, symbol)
        result["anomalies"] = anomalies

        if df.empty:
            logger.warning(
                f"[{symbol}] All data removed after cleaning, skipping aggregation."
            )
            return result

        # 3. Compute daily volume before resampling (use 1-min data)
        daily_vol = compute_daily_volume(df)
        result["daily_volume_df"] = daily_vol

        # 4. Export canonical 1-min Parquet
        minute_subdir = minute_output_subdir or default_config.minute_output_subdir
        one_min_dir = os.path.join(output_dir, minute_subdir)
        os.makedirs(one_min_dir, exist_ok=True)
        minute_parquet_path = os.path.join(one_min_dir, f"{symbol}.parquet")
        df.to_parquet(minute_parquet_path, index=False)
        result["minute_parquet_path"] = minute_parquet_path
        logger.info(
            f"[{symbol}] 1-min Parquet written: {minute_parquet_path}  ({len(df)} rows)"
        )

        # Publish the same historical rows to the canonical, date-partitioned
        # market store.  Legacy output above remains intact for existing users.
        if market_root:
            _publish_market_partitions(df, market_root)

        # 5. Resample to 5-min
        df_5min = resample_to_5min(df)
        if df_5min.empty:
            logger.warning(f"[{symbol}] No 5-min bars after resampling.")
            return result

        # 6. Calculate MAs
        df_5min = calculate_moving_averages(df_5min)

        # Sort by time
        if "bob" in df_5min.columns:
            df_5min = df_5min.sort_values("bob").reset_index(drop=True)

        # 7. Export canonical 5-min Parquet
        kline_subdir = kline_output_subdir or default_config.kline_output_subdir
        five_min_dir = os.path.join(output_dir, kline_subdir)
        os.makedirs(five_min_dir, exist_ok=True)
        parquet_name = f"{symbol}.parquet"
        parquet_path = os.path.join(five_min_dir, parquet_name)
        df_5min.to_parquet(parquet_path, index=False)
        result["parquet_path"] = parquet_path
        logger.info(
            f"[{symbol}] 5-min Parquet written: {parquet_path}  ({len(df_5min)} rows)"
        )

        # 8. Write to InfluxDB
        points = save_to_influxdb(df_5min, influx_config)
        result["points_written"] = points

    except Exception as e:
        logger.error(f"[{symbol}] Processing failed: {e}")
        result["error"] = f"{symbol}: {e}\n{traceback.format_exc()}"

    return result


def discover_csv_files(input_dir: str) -> list[str]:
    """Find all CSV files in the input directory."""
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    csv_files = sorted(
        [
            os.path.join(input_dir, f)
            for f in os.listdir(input_dir)
            if f.lower().endswith(".csv")
        ]
    )
    logger.info(f"Discovered {len(csv_files)} CSV files in {input_dir}")
    return csv_files


def run_pipeline(cfg: Optional[PipelineConfig] = None) -> dict:
    """
    Run the full data pipeline.

    Returns a summary dict with keys:
      - total_contracts: int
      - successful: int
      - failed: int
      - anomalies_count: int
      - daily_volume_path: str
      - quality_log_path: str
    """
    if cfg is None:
        cfg = default_config

    # Resolve data paths against the repository root while keeping imports rooted
    # at data_pipeline for spawned worker processes.
    pipeline_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_root = os.path.dirname(pipeline_root)
    input_dir = (
        cfg.input_dir
        if os.path.isabs(cfg.input_dir)
        else os.path.join(project_root, cfg.input_dir)
    )
    output_dir = (
        cfg.output_dir
        if os.path.isabs(cfg.output_dir)
        else os.path.join(project_root, cfg.output_dir)
    )

    csv_files = discover_csv_files(input_dir)
    if not csv_files:
        logger.warning("No CSV files found. Pipeline exiting.")
        return {
            "total_contracts": 0,
            "successful": 0,
            "failed": 0,
            "anomalies_count": 0,
            "daily_volume_path": "",
            "quality_log_path": "",
        }

    os.makedirs(output_dir, exist_ok=True)

    # InfluxDB config needs to be picklable for multiprocessing; extract to plain dataclass
    influx_config = cfg.influx

    logger.info(
        f"Starting pipeline: {len(csv_files)} contracts, {cfg.max_workers} workers"
    )

    all_anomalies: list[AnomalyRecord] = []
    daily_volumes: list[pd.DataFrame] = []
    successful = 0
    failed = 0

    with ProcessPoolExecutor(
        max_workers=cfg.max_workers,
        initializer=_worker_initializer,
        initargs=(pipeline_root,),
    ) as executor:
        future_to_file = {
            executor.submit(
                process_single_contract,
                f,
                output_dir,
                influx_config,
                cfg.minute_output_subdir,
                cfg.kline_output_subdir,
                cfg.market_root,
            ): f
            for f in csv_files
        }

        for future in as_completed(future_to_file):
            csv_file = future_to_file[future]
            try:
                result = future.result()
                if result["error"]:
                    logger.error(f"Contract failed: {result['error']}")
                    failed += 1
                else:
                    successful += 1

                all_anomalies.extend(result.get("anomalies", []))
                if (
                    result.get("daily_volume_df") is not None
                    and not result["daily_volume_df"].empty
                ):
                    daily_volumes.append(result["daily_volume_df"])

            except Exception as e:
                logger.error(f"Worker crashed for {csv_file}: {e}")
                failed += 1

    # Write quality log
    quality_log_path = os.path.join(output_dir, cfg.quality_log_file)
    write_quality_log(all_anomalies, quality_log_path)
    logger.info(
        f"Quality log written: {quality_log_path}  ({len(all_anomalies)} anomalies)"
    )

    # Compute and write daily volume summary
    daily_summary = compute_daily_volume_summary(daily_volumes)
    daily_volume_path = os.path.join(output_dir, cfg.daily_volume_file)
    daily_summary.to_parquet(daily_volume_path, index=False)
    logger.info(
        f"Daily volume summary written: {daily_volume_path}  ({len(daily_summary)} rows)"
    )

    summary = {
        "total_contracts": len(csv_files),
        "successful": successful,
        "failed": failed,
        "anomalies_count": len(all_anomalies),
        "daily_volume_path": daily_volume_path,
        "quality_log_path": quality_log_path,
    }

    logger.info(f"Pipeline complete: {summary}")
    return summary


def _worker_initializer(pipeline_root: str) -> None:
    """
    Initializer for ProcessPoolExecutor workers.

    On Windows (spawn start method), each worker is a fresh Python process
    that does not inherit sys.path from the parent.  This ensures the project
    pipeline root is on sys.path so `from src.xxx` imports resolve in workers.
    """
    import sys

    if pipeline_root not in sys.path:
        sys.path.insert(0, pipeline_root)


def _publish_market_partitions(df: pd.DataFrame, market_root: str) -> None:
    """Publish cleaned history once per exchange/instrument/trading-date."""
    required_columns = {"exchange", "symbol", "bob"}
    if not required_columns.issubset(df.columns):
        logger.warning("Skipping canonical market publish: missing partition columns")
        return

    partitioned = df.assign(
        _trading_date=pd.to_datetime(df["bob"], utc=True).dt.date,
    )
    for (exchange, instrument, trading_date), rows in partitioned.groupby(
        ["exchange", "symbol", "_trading_date"], sort=False
    ):
        partition = MarketPartition(
            source="ctp",
            exchange=str(exchange),
            instrument=str(instrument),
            trading_date=trading_date,
        )
        target = partition_path(market_root, partition)
        table = pa.Table.from_pandas(
            rows.drop(columns=["_trading_date", "exchange", "symbol"]),
            preserve_index=False,
        )
        publish_parquet(table, target)
        logger.info("[%s] Canonical market Parquet written: %s", instrument, target)
