"""Canonical 1-minute parquet market data for the quant runtime.

业务功能: 读取 data/output/1min 下的标准 1 分钟 parquet 行情，供 VNPY 导入
和回测使用。
算法要点: 输入文件必须包含 canonical 字段集合；读取后按 symbol 和时间范围
过滤，并转换成与 VNPY BarData 字段一一对应的 NormalizedBar。
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

import pandas as pd

from quant_runtime.settings import settings


REQUIRED_COLUMNS = {
    "exchange",
    "symbol",
    "eob",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "position",
}
SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class NormalizedBar:
    """业务功能: quant_runtime 内部统一使用的 1 分钟 K 线结构。"""

    exchange: str
    symbol: str
    datetime: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    turnover: float
    open_interest: float


class MarketDataError(Exception):
    """业务功能: 表示 canonical parquet 行情不可读取或不符合规范。"""


def _symbol_parquet_path(symbol: str, data_dir: Path) -> Path:
    """业务功能: 将 symbol 映射到 1 分钟 parquet 文件。

    算法要点: symbol 字符白名单加 resolve 父目录检查，防止路径穿越。
    """
    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise MarketDataError(
            "symbol may only contain letters, numbers, underscore, dash and dot",
        )

    root = data_dir.resolve()
    path = (root / f"{symbol}.parquet").resolve()
    if root not in path.parents:
        raise MarketDataError("invalid symbol path")
    if not path.exists():
        raise MarketDataError(f"contract parquet not found: data/output/1min/{symbol}.parquet")
    return path


def _parse_datetime(value) -> datetime:
    """算法要点: 兼容 pandas Timestamp、datetime 和 ISO/Z 字符串。"""
    timestamp = pd.to_datetime(value)
    if isinstance(timestamp, pd.Timestamp):
        return timestamp.to_pydatetime()
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _in_range(
    value: datetime,
    start_time: datetime | None,
    end_time: datetime | None,
) -> bool:
    """算法要点: 比较时间范围前先对齐边界和 bar_time 的 tzinfo。"""
    def align_boundary(boundary: datetime | None) -> datetime | None:
        if boundary is None:
            return None
        if value.tzinfo is not None and boundary.tzinfo is None:
            return boundary.replace(tzinfo=value.tzinfo)
        if value.tzinfo is None and boundary.tzinfo is not None:
            return boundary.replace(tzinfo=None)
        return boundary

    start_time = align_boundary(start_time)
    end_time = align_boundary(end_time)
    if start_time is not None and value < start_time:
        return False
    if end_time is not None and value > end_time:
        return False
    return True


def list_symbols(data_dir: Path = settings.minute_data_dir) -> list[str]:
    """业务功能: 列出当前 1 分钟行情目录下可回测的合约代码。"""
    if not data_dir.exists():
        return []
    return sorted(path.stem for path in data_dir.glob("*.parquet") if path.is_file())


def read_minute_bars(
    symbol: str,
    data_dir: Path = settings.minute_data_dir,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[NormalizedBar]:
    """业务功能: 读取一个合约在可选时间范围内的标准 1 分钟 K 线。

    算法要点: 先校验 canonical 字段完整性，再逐行过滤 symbol 和时间范围；
    字段类型在进入回测引擎前统一转换为 str/float/datetime。
    """
    path = _symbol_parquet_path(symbol, data_dir)
    frame = pd.read_parquet(path)
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise MarketDataError(
            "parquet missing required columns: "
            + ", ".join(missing)
            + "; available columns: "
            + ", ".join(frame.columns),
        )

    bars: list[NormalizedBar] = []
    for row in frame.to_dict("records"):
        bar_time = _parse_datetime(row["eob"])
        if row["symbol"] != symbol or not _in_range(bar_time, start_time, end_time):
            continue
        bars.append(
            NormalizedBar(
                exchange=str(row["exchange"]),
                symbol=str(row["symbol"]),
                datetime=bar_time,
                open_price=float(row["open"]),
                high_price=float(row["high"]),
                low_price=float(row["low"]),
                close_price=float(row["close"]),
                volume=float(row["volume"]),
                turnover=float(row["amount"]),
                open_interest=float(row["position"]),
            ),
        )
    return bars
