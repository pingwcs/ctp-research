"""Build quant-runtime runner payloads from HTTP backtest requests."""

from typing import Any

from appapi.schemas.backtest import BacktestRunRequest


def build_runner_payload(request: BacktestRunRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "symbol": request.symbol,
        "metrics": request.metrics,
    }
    if request.strategy:
        payload["strategy"] = request.strategy
    if request.start_time is not None:
        payload["start_time"] = request.start_time
    if request.end_time is not None:
        payload["end_time"] = request.end_time
    return payload
