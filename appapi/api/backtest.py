"""Backtest HTTP endpoints."""

from fastapi import APIRouter

from appapi.schemas.backtest import (
    BacktestRunRequest,
    BacktestRunResponse,
    MetricInfo,
    StrategyInfo,
)
from appapi.services.backtest import (
    METRICS,
    STRATEGIES,
    list_backtest_symbols,
    run_backtest,
)


router = APIRouter()


@router.get("/strategies", response_model=list[StrategyInfo])
def get_strategies() -> list[StrategyInfo]:
    return STRATEGIES


@router.get("/symbols", response_model=list[str])
def get_symbols() -> list[str]:
    return list_backtest_symbols()


@router.get("/metrics", response_model=list[MetricInfo])
def get_metrics() -> list[MetricInfo]:
    return METRICS


@router.post("/run", response_model=BacktestRunResponse)
def post_run_backtest(request: BacktestRunRequest) -> BacktestRunResponse:
    return run_backtest(request)
