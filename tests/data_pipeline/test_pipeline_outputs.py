"""Tests for canonical parquet outputs produced by the data pipeline."""

import sys
from pathlib import Path

import pandas as pd

PIPELINE_ROOT = Path(__file__).resolve().parents[2] / "data_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.config import InfluxDBConfig
from src.pipeline import process_single_contract


def test_process_single_contract_writes_1min_and_5min_read_models(tmp_path: Path):
    csv_path = tmp_path / "RB0909.csv"
    rows = []
    for minute in range(5):
        rows.append(
            {
                "exchange": "SHFE",
                "symbol": "RB0909",
                "bob": f"2009-03-27 09:0{minute}:00+08:00",
                "eob": f"2009-03-27 09:0{minute}:00+08:00",
                "open": 3550.0 + minute,
                "high": 3560.0 + minute,
                "low": 3540.0 + minute,
                "close": 3555.0 + minute,
                "volume": 10.0 + minute,
                "amount": 1000.0 + minute,
                "position": 100.0 + minute,
            },
        )
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    output_dir = tmp_path / "output"
    result = process_single_contract(
        str(csv_path),
        str(output_dir),
        InfluxDBConfig(enabled=False),
    )

    assert result["error"] is None
    one_min_path = output_dir / "1min" / "RB0909.parquet"
    five_min_path = output_dir / "5min" / "RB0909.parquet"
    assert one_min_path.exists()
    assert five_min_path.exists()
    assert result["parquet_path"] == str(five_min_path)

    one_min = pd.read_parquet(one_min_path)
    five_min = pd.read_parquet(five_min_path)
    assert len(one_min) == 5
    assert len(five_min) == 1
    assert "ma5" in five_min.columns
