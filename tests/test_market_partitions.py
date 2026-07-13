from datetime import date
from pathlib import Path
import subprocess
import sys

from market_data.partitions import MarketPartition, partition_path


def test_partition_path_uses_canonical_hive_layout(tmp_path):
    partition = MarketPartition("ctp", "SHFE", "rb2410", date(2026, 7, 13))

    path = partition_path(tmp_path, partition)

    assert path == (
        tmp_path
        / "source=ctp"
        / "exchange=SHFE"
        / "instrument=rb2410"
        / "trading_date=2026-07-13"
        / "ticks.parquet"
    )


def test_pipeline_help_includes_market_root_option():
    project_root = Path(__file__).resolve().parents[1]

    completed = subprocess.run(
        [sys.executable, "data_pipeline/run.py", "--help"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "--market-root" in completed.stdout
