"""Atomic writers for canonical market-data files."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import pyarrow as pa
import pyarrow.parquet as pq


def publish_parquet(table: pa.Table, target: str | Path) -> Path:
    """Write *table* atomically, replacing ``target`` only once it is complete."""
    destination = Path(target)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with NamedTemporaryFile(
        mode="wb", suffix=".tmp", prefix=f".{destination.name}.",
        dir=destination.parent, delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)

    try:
        pq.write_table(table, temporary_path)
        os.replace(temporary_path, destination)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise

    return destination
