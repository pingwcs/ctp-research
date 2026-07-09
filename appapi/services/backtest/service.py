"""API-facing backtest service that delegates execution to quant runtime."""

from typing import Any

from fastapi import HTTPException, status

from appapi.schemas.backtest import BacktestRunRequest, BacktestRunResponse
from appapi.services.backtest.catalog import (
    available_metric_ids,
    available_strategy_ids,
)
from appapi.services.backtest.mappers import to_backtest_run_response
from appapi.services.backtest.runner_client import invoke_runner


def _request_payload(request: BacktestRunRequest) -> dict[str, Any]:
    return {
        "symbol": request.symbol,
        "strategy": request.strategy,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "metrics": request.metrics,
    }


def _validate_request(request: BacktestRunRequest) -> None:
    if request.strategy not in available_strategy_ids():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported strategy: {request.strategy}",
        )
    selected = request.metrics or sorted(available_metric_ids())
    invalid = [
        metric for metric in selected
        if metric not in available_metric_ids()
    ]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported metrics: {', '.join(invalid)}",
        )
    if (
        request.start_time is not None
        and request.end_time is not None
        and request.start_time > request.end_time
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be before end_time",
        )


def run_backtest(request: BacktestRunRequest) -> BacktestRunResponse:
    _validate_request(request)
    payload = invoke_runner("run", _request_payload(request))
    return to_backtest_run_response(payload)
