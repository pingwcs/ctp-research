"""Backtest HTTP endpoints."""

from fastapi import APIRouter

from appapi.schemas.backtest import (
    BacktestRunRequest,
    BacktestRunResponse,
    MetricInfo,
    StrategyInfo,
)
from appapi.services.backtest import (
    get_metrics,
    get_strategies,
    list_backtest_symbols,
    run_backtest,
)


router = APIRouter()


@router.get("/strategies", response_model=list[StrategyInfo])
def list_strategies() -> list[StrategyInfo]:
    return get_strategies()


@router.get("/symbols", response_model=list[str])
def get_symbols() -> list[str]:
    return list_backtest_symbols()


@router.get("/metrics", response_model=list[MetricInfo])
def list_metrics() -> list[MetricInfo]:
    return get_metrics()


@router.post("/run", response_model=BacktestRunResponse)
def post_run_backtest(request: BacktestRunRequest) -> BacktestRunResponse:
    return run_backtest(request)
