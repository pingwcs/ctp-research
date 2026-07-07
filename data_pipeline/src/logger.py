"""
Cross-process safe logging for the futures data pipeline.

Each worker process returns a list of anomaly dictionaries. The main process
collects and writes them to CSV after all workers complete. This avoids the
complexity of shared queues while keeping the design simple and robust.

Log record schema:
    [file_name, symbol, row_index, field, original_value, corrected_value, anomaly_type, detail]
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import csv
import os


@dataclass
class AnomalyRecord:
    """A single data-quality anomaly entry."""

    file_name: str
    symbol: str
    row_index: int
    field: str
    original_value: str
    corrected_value: str
    anomaly_type: str  # timestamp_rounding | missing_value_filled | duplicate_merged
    detail: str = ""  # e.g. fill direction, duplicate keys


def collect_worker_logs(worker_results: list) -> list[AnomalyRecord]:
    """Flatten anomaly records from all worker results into a single list."""
    all_logs: list[AnomalyRecord] = []
    for result in worker_results:
        if result and "anomalies" in result:
            all_logs.extend(result["anomalies"])
    return all_logs


def write_quality_log(anomalies: list[AnomalyRecord], path: str) -> str:
    """Write collected anomaly records to CSV. Returns the file path."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if not anomalies:
        # Write empty file with header so consumers know the format
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "file_name",
                    "symbol",
                    "row_index",
                    "field",
                    "original_value",
                    "corrected_value",
                    "anomaly_type",
                    "detail",
                ]
            )
        return path

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "file_name",
                "symbol",
                "row_index",
                "field",
                "original_value",
                "corrected_value",
                "anomaly_type",
                "detail",
            ]
        )
        for a in anomalies:
            writer.writerow(
                [
                    a.file_name,
                    a.symbol,
                    a.row_index,
                    a.field,
                    a.original_value,
                    a.corrected_value,
                    a.anomaly_type,
                    a.detail,
                ]
            )
    return path
