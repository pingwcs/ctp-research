"""vn.py historical bar database import utilities."""

from collections.abc import Iterable
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from quant_runtime.contracts import RunnerError
from quant_runtime.market_data import MarketDataError, NormalizedBar, read_minute_bars
from quant_runtime.settings import prepare_vnpy_runtime, settings


IMPORT_MANIFEST_FILENAME = "bar_import_manifest.json"


def _chunks(values: list[NormalizedBar], chunk_size: int) -> Iterable[list[NormalizedBar]]:
    for index in range(0, len(values), chunk_size):
        yield values[index : index + chunk_size]


def _to_vnpy_bar(bar: NormalizedBar):
    prepare_vnpy_runtime()

    from vnpy.trader.constant import Exchange, Interval
    from vnpy.trader.object import BarData

    return BarData(
        symbol=bar.symbol,
        exchange=Exchange(bar.exchange),
        datetime=bar.datetime,
        interval=Interval.MINUTE,
        volume=bar.volume,
        turnover=bar.turnover,
        open_interest=bar.open_interest,
        open_price=bar.open_price,
        high_price=bar.high_price,
        low_price=bar.low_price,
        close_price=bar.close_price,
        gateway_name="PARQUET",
    )


def _manifest_path() -> Path:
    return settings.runtime_dir / IMPORT_MANIFEST_FILENAME


def _load_manifest() -> dict[str, Any]:
    path = _manifest_path()
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _save_manifest(manifest: dict[str, Any]) -> None:
    path = _manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _time_key(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _source_path(symbol: str, minute_data_dir: Path) -> Path:
    return (minute_data_dir.resolve() / f"{symbol}.parquet").resolve()


def _import_fingerprint(
    symbol: str,
    minute_data_dir: Path,
    start_time: datetime | None,
    end_time: datetime | None,
    bars: list[NormalizedBar],
) -> dict[str, Any]:
    parquet_path = _source_path(symbol, minute_data_dir)
    stat = parquet_path.stat()
    return {
        "symbol": symbol,
        "minute_data_dir": str(minute_data_dir.resolve()),
        "source_path": str(parquet_path),
        "source_mtime_ns": stat.st_mtime_ns,
        "source_size": stat.st_size,
        "start_time": _time_key(start_time),
        "end_time": _time_key(end_time),
        "bar_count": len(bars),
    }


def _manifest_key(symbol: str, minute_data_dir: Path) -> str:
    return f"{minute_data_dir.resolve()}::{symbol}"


def _fresh_import_exists(
    symbol: str,
    minute_data_dir: Path,
    fingerprint: dict[str, Any],
) -> bool:
    manifest = _load_manifest()
    return manifest.get(_manifest_key(symbol, minute_data_dir)) == fingerprint


def _mark_import_fresh(
    symbol: str,
    minute_data_dir: Path,
    fingerprint: dict[str, Any],
) -> None:
    manifest = _load_manifest()
    manifest[_manifest_key(symbol, minute_data_dir)] = fingerprint
    _save_manifest(manifest)


def _read_symbol_bars(
    symbol: str,
    minute_data_dir: Path,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[NormalizedBar]:
    try:
        return read_minute_bars(symbol, minute_data_dir, start_time, end_time)
    except MarketDataError as exc:
        raise RunnerError(404, str(exc)) from exc


def _ensure_symbol_bars_imported(
    symbol: str,
    minute_data_dir: Path,
    start_time: datetime | None,
    end_time: datetime | None,
    bars: list[NormalizedBar],
    chunk_size: int,
) -> int:
    if not bars:
        raise RunnerError(404, "no bars found for the requested symbol and time range")

    fingerprint = _import_fingerprint(
        symbol,
        minute_data_dir,
        start_time,
        end_time,
        bars,
    )
    if _fresh_import_exists(symbol, minute_data_dir, fingerprint):
        return len(bars)

    from vnpy.trader.constant import Exchange, Interval
    from vnpy.trader.database import get_database

    database = get_database()
    exchange = Exchange(bars[0].exchange)
    database.delete_bar_data(symbol, exchange, Interval.MINUTE)

    saved = 0
    for batch in _chunks(bars, chunk_size):
        database.save_bar_data([_to_vnpy_bar(bar) for bar in batch])
        saved += len(batch)
    _mark_import_fresh(symbol, minute_data_dir, fingerprint)
    return saved


def prepare_symbol_bars(
    symbol: str,
    minute_data_dir: Path,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    chunk_size: int = 2000,
) -> list[NormalizedBar]:
    prepare_vnpy_runtime()
    bars = _read_symbol_bars(symbol, minute_data_dir, start_time, end_time)
    _ensure_symbol_bars_imported(
        symbol,
        minute_data_dir,
        start_time,
        end_time,
        bars,
        chunk_size,
    )
    return bars


def import_symbol_bars(
    symbol: str,
    minute_data_dir: Path,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    chunk_size: int = 2000,
) -> int:
    return len(
        prepare_symbol_bars(
            symbol,
            minute_data_dir,
            start_time,
            end_time,
            chunk_size,
        ),
    )
