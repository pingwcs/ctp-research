from datetime import date
from pathlib import Path
import sys

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

PIPELINE_ROOT = Path(__file__).resolve().parents[1] / "data_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.pipeline import _publish_market_partitions
from market_data.writer import publish_parquet


def test_publish_parquet_atomically_creates_readable_target_without_temp_file(tmp_path):
    target = tmp_path / "market" / "ticks.parquet"

    result = publish_parquet(pa.table({"price": [1, 2]}), target)

    assert result == target
    assert pq.read_table(target).to_pydict() == {"price": [1, 2]}
    assert list(target.parent.glob("*.tmp")) == []


def test_publish_parquet_keeps_existing_target_when_write_fails(tmp_path, monkeypatch):
    target = tmp_path / "market" / "ticks.parquet"
    publish_parquet(pa.table({"price": [1, 2]}), target)

    def fail_write(*_args, **_kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(pq, "write_table", fail_write)

    with pytest.raises(RuntimeError, match="disk full"):
        publish_parquet(pa.table({"price": [3]}), target)

    assert pq.read_table(target).to_pydict() == {"price": [1, 2]}
    assert list(target.parent.glob("*.tmp")) == []


def test_pipeline_publishes_cleaned_history_to_canonical_partition(tmp_path):
    frame = pd.DataFrame(
        {
            "exchange": ["SHFE"],
            "symbol": ["rb2410"],
            "bob": ["2026-07-13T01:00:00Z"],
            "price": [1],
        }
    )

    _publish_market_partitions(frame, str(tmp_path))

    target = (
        tmp_path
        / "source=ctp"
        / "exchange=SHFE"
        / "instrument=rb2410"
        / "trading_date=2026-07-13"
        / "ticks.parquet"
    )
    assert pq.read_table(target).column("price").to_pylist() == [1]
