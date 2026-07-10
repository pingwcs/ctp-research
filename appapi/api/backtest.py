"""Backtest HTTP endpoints."""

from fastapi import APIRouter

from appapi.schemas.backtest import (
    BacktestJobStatusResponse,
    BacktestJobSubmitResponse,
    BacktestRunRequest,
    BacktestRunResponse,
    MetricInfo,
    StrategyInfo,
)
from appapi.services.backtest import (
    get_backtest_job_result,
    get_backtest_job_status,
    get_metrics,
    get_strategies,
    list_backtest_symbols,
    run_backtest,
    submit_backtest_job,
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


@router.post("/jobs", response_model=BacktestJobSubmitResponse)
def post_submit_backtest_job(request: BacktestRunRequest) -> BacktestJobSubmitResponse:
    return submit_backtest_job(request)


@router.get("/jobs/{job_id}", response_model=BacktestJobStatusResponse)
def get_backtest_job(job_id: str) -> BacktestJobStatusResponse:
    return get_backtest_job_status(job_id)


@router.get("/jobs/{job_id}/result", response_model=BacktestRunResponse)
def get_backtest_job_result_endpoint(job_id: str) -> BacktestRunResponse:
    return get_backtest_job_result(job_id)
