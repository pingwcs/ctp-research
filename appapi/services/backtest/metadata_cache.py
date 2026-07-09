"""Small runtime metadata cache for appapi backtest endpoints."""

from time import monotonic
from typing import Any

from appapi.services.backtest.runner_client import invoke_runner


_CACHE_TTL_SECONDS = 30.0
_cached_payload: dict[str, Any] | None = None
_cached_at = 0.0


def clear_metadata_cache() -> None:
    global _cached_at, _cached_payload
    _cached_payload = None
    _cached_at = 0.0


def runtime_metadata() -> dict[str, Any]:
    global _cached_at, _cached_payload
    now = monotonic()
    if _cached_payload is not None and now - _cached_at < _CACHE_TTL_SECONDS:
        return _cached_payload

    _cached_payload = invoke_runner("metadata")
    _cached_at = now
    return _cached_payload
