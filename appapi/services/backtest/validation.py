"""HTTP request validation for backtest runs."""

from fastapi import HTTPException, status

from appapi.schemas.backtest import BacktestRunRequest
from appapi.services.backtest.catalog import (
    available_metric_ids,
    available_strategy_ids,
)


def validate_backtest_request(request: BacktestRunRequest) -> None:
    if request.strategy is not None and request.strategy not in available_strategy_ids():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported strategy: {request.strategy}",
        )

    metric_ids = available_metric_ids()
    selected = request.metrics or sorted(metric_ids)
    invalid = [metric for metric in selected if metric not in metric_ids]
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
