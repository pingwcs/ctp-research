"""Small runtime metadata cache for appapi backtest endpoints.

业务功能: 缓存策略和指标元数据，减少前端频繁刷新时的 runner 启动次数。
算法要点: 使用 monotonic 计时做 30 秒 TTL，避免系统时间调整导致缓存
过期判断异常。
"""

from time import monotonic
from typing import Any

from appapi.services.backtest.runner_client import invoke_runner


_CACHE_TTL_SECONDS = 30.0
_cached_payload: dict[str, Any] | None = None
_cached_at = 0.0


def clear_metadata_cache() -> None:
    """业务功能: 测试或配置热更新时清空元数据缓存。"""
    global _cached_at, _cached_payload
    _cached_payload = None
    _cached_at = 0.0


def runtime_metadata() -> dict[str, Any]:
    """业务功能: 获取运行时元数据，并在 TTL 内复用最近一次结果。"""
    global _cached_at, _cached_payload
    now = monotonic()
    if _cached_payload is not None and now - _cached_at < _CACHE_TTL_SECONDS:
        return _cached_payload

    _cached_payload = invoke_runner("metadata")
    _cached_at = now
    return _cached_payload
