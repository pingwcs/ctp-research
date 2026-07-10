"""vn.py historical bar database import utilities.

业务功能: 将 canonical 1 分钟 parquet 行情导入 vn.py 数据库，供
BacktestingEngine.load_data 使用。
算法要点: 用导入指纹记录源文件 mtime/size、时间范围和 bar 数量；指纹一致
时跳过重复导入，指纹变化时先删除旧 bar 再批量写入，保证数据库和源文件一致。
"""

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
    """算法要点: 将大批量 bar 拆成固定大小批次写入数据库。"""
    for index in range(0, len(values), chunk_size):
        yield values[index : index + chunk_size]


def _to_vnpy_bar(bar: NormalizedBar):
    """业务功能: 将 NormalizedBar 转换为 vn.py BarData。"""
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
    """业务功能: 返回导入指纹 manifest 文件路径。"""
    return settings.runtime_dir / IMPORT_MANIFEST_FILENAME


def _load_manifest() -> dict[str, Any]:
    """业务功能: 读取导入指纹 manifest，损坏时按空缓存处理。"""
    path = _manifest_path()
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _save_manifest(manifest: dict[str, Any]) -> None:
    """业务功能: 持久化导入指纹 manifest。"""
    path = _manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _time_key(value: datetime | None) -> str | None:
    """算法要点: 时间范围边界用 ISO 字符串参与指纹比较。"""
    return value.isoformat() if value is not None else None


def _source_path(symbol: str, minute_data_dir: Path) -> Path:
    """业务功能: 构造源 parquet 路径用于指纹采集。"""
    return (minute_data_dir.resolve() / f"{symbol}.parquet").resolve()


def _import_fingerprint(
    symbol: str,
    minute_data_dir: Path,
    start_time: datetime | None,
    end_time: datetime | None,
    bars: list[NormalizedBar],
) -> dict[str, Any]:
    """算法要点: 组合源文件元数据、时间范围和 bar 数量形成导入指纹。"""
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
    """算法要点: 同一 symbol 在不同数据目录下拥有独立导入缓存。"""
    return f"{minute_data_dir.resolve()}::{symbol}"


def _fresh_import_exists(
    symbol: str,
    minute_data_dir: Path,
    fingerprint: dict[str, Any],
) -> bool:
    """业务功能: 判断当前 vn.py 数据库中是否已有匹配源数据的导入结果。"""
    manifest = _load_manifest()
    return manifest.get(_manifest_key(symbol, minute_data_dir)) == fingerprint


def _mark_import_fresh(
    symbol: str,
    minute_data_dir: Path,
    fingerprint: dict[str, Any],
) -> None:
    """业务功能: 标记本次导入结果已与源数据保持一致。"""
    manifest = _load_manifest()
    manifest[_manifest_key(symbol, minute_data_dir)] = fingerprint
    _save_manifest(manifest)


def _read_symbol_bars(
    symbol: str,
    minute_data_dir: Path,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[NormalizedBar]:
    """业务功能: 读取源行情并把 MarketDataError 转换为 runner 协议错误。"""
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
    """业务功能: 确保指定合约 bar 已导入 vn.py 数据库。

    算法要点: 空数据直接作为 404；指纹命中时返回 bar 数量；未命中时删除
    当前 symbol 的分钟数据后分批保存，避免新旧源文件混合。
    """
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
    """业务功能: 准备回测所需的 VNPY 数据库 bar，并返回本次使用的 bar。"""
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
    """业务功能: 显式导入一个合约的分钟 bar，并返回可用 bar 数量。"""
    return len(
        prepare_symbol_bars(
            symbol,
            minute_data_dir,
            start_time,
            end_time,
            chunk_size,
        ),
    )
