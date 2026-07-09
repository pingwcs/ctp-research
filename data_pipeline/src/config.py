"""
Configuration module for the futures data pipeline.
All settings are sourced from environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass, field


@dataclass
class InfluxDBConfig:
    url: str = os.getenv("INFLUXDB_URL", "http://localhost:8086")
    token: str = os.getenv("INFLUXDB_TOKEN", "")
    org: str = os.getenv("INFLUXDB_ORG", "default")
    bucket: str = os.getenv("INFLUXDB_BUCKET", "futures_data")
    measurement: str = "futures_5min_bars"
    batch_size: int = int(os.getenv("INFLUXDB_BATCH_SIZE", "5000"))
    write_timeout_ms: int = int(os.getenv("INFLUXDB_WRITE_TIMEOUT_MS", "30000"))
    enabled: bool = os.getenv("INFLUXDB_ENABLED", "1").lower() not in (
        "0",
        "false",
        "no",
    )


@dataclass
class PipelineConfig:
    mode: str = os.getenv("PIPELINE_MODE", "test")  # Options: 'daily', 'historical'
    data_prefix: str = "data/test" if mode == "test" else "data"
    input_dir: str = os.getenv("PIPELINE_INPUT_DIR", data_prefix + "/input")
    output_dir: str = os.getenv("PIPELINE_OUTPUT_DIR", data_prefix + "/output")
    minute_output_subdir: str = "1min"
    kline_output_subdir: str = "5min"
    max_workers: int = int(os.getenv("PIPELINE_MAX_WORKERS", str(os.cpu_count() or 4)))
    daily_volume_file: str = "daily_volume_summary.parquet"
    quality_log_file: str = "data_quality_log.csv"
    influx: InfluxDBConfig = field(default_factory=InfluxDBConfig)


config = PipelineConfig()
