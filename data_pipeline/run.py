"""
Command-line entry point for the futures data pipeline.

Usage:
    python data_pipeline/run.py
    python data_pipeline/run.py --input-dir data/input --output-dir data/output --workers 4
    python data_pipeline/run.py --no-influx

Environment variables (see data_pipeline/src/config.py for all):
    INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET
    PIPELINE_INPUT_DIR, PIPELINE_OUTPUT_DIR, PIPELINE_MAX_WORKERS
    INFLUXDB_ENABLED
"""

import argparse
import logging
import os
import sys

# Ensure data_pipeline/src is importable when launched from the project root.
PIPELINE_ROOT = os.path.dirname(os.path.abspath(__file__))
if PIPELINE_ROOT not in sys.path:
    sys.path.insert(0, PIPELINE_ROOT)

from src.config import PipelineConfig, InfluxDBConfig, config as default_config
from src.pipeline import run_pipeline


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Futures Contract Minute Data Cleaning & Synthesis Pipeline"
    )
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Directory containing input CSV files (default: data/input)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for output Parquet/log files (default: data/output)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help=f"Number of worker processes (default: CPU count, currently {os.cpu_count() or 4})",
    )
    parser.add_argument(
        "--no-influx", action="store_true", help="Disable InfluxDB writing"
    )
    parser.add_argument("--influx-url", default=None, help="InfluxDB server URL")
    parser.add_argument(
        "--influx-token", default=None, help="InfluxDB authentication token"
    )
    parser.add_argument("--influx-org", default=None, help="InfluxDB organization")
    parser.add_argument("--influx-bucket", default=None, help="InfluxDB bucket name")
    parser.add_argument(
        "--influx-batch-size", type=int, default=None, help="InfluxDB write batch size"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    args = parser.parse_args()

    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # Build config from CLI overrides + env vars
    influx = InfluxDBConfig()
    if args.no_influx:
        influx.enabled = False
    if args.influx_url:
        influx.url = args.influx_url
    if args.influx_token:
        influx.token = args.influx_token
    if args.influx_org:
        influx.org = args.influx_org
    if args.influx_bucket:
        influx.bucket = args.influx_bucket
    if args.influx_batch_size:
        influx.batch_size = args.influx_batch_size

    pipeline_cfg = PipelineConfig(influx=influx)
    if args.input_dir:
        pipeline_cfg.input_dir = args.input_dir
    if args.output_dir:
        pipeline_cfg.output_dir = args.output_dir
    if args.workers:
        pipeline_cfg.max_workers = args.workers

    logger.info("=" * 60)
    logger.info("Futures Data Pipeline Starting")
    logger.info(f"  Input dir:    {pipeline_cfg.input_dir}")
    logger.info(f"  Output dir:   {pipeline_cfg.output_dir}")
    logger.info(f"  Workers:      {pipeline_cfg.max_workers}")
    logger.info(
        f"  InfluxDB:     {'enabled' if pipeline_cfg.influx.enabled else 'disabled'}"
    )
    if pipeline_cfg.influx.enabled:
        logger.info(f"  InfluxDB URL: {pipeline_cfg.influx.url}")
        logger.info(f"  InfluxDB Org: {pipeline_cfg.influx.org}")
        logger.info(f"  InfluxDB Bkt: {pipeline_cfg.influx.bucket}")
    logger.info("=" * 60)

    summary = run_pipeline(pipeline_cfg)

    logger.info("=" * 60)
    logger.info("Pipeline Summary")
    logger.info(f"  Contracts total:     {summary['total_contracts']}")
    logger.info(f"  Successful:          {summary['successful']}")
    logger.info(f"  Failed:              {summary['failed']}")
    logger.info(f"  Anomalies logged:    {summary['anomalies_count']}")
    logger.info(f"  Daily volume:        {summary['daily_volume_path']}")
    logger.info(f"  Quality log:         {summary['quality_log_path']}")
    logger.info("=" * 60)

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
