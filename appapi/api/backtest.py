"""Backtest HTTP endpoints.

业务功能: 提供策略/指标/标的发现、同步回测和异步回测任务查询接口。
算法要点: appapi 不模拟策略，只把 HTTP 请求转交 quant_runtime，并把
运行时返回的领域结果映射成前端稳定 schema。
"""

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
    """业务功能: 查询 quant_runtime 当前注册的回测策略元数据。"""
    return get_strategies()


@router.get("/symbols", response_model=list[str])
def get_symbols() -> list[str]:
    """业务功能: 查询可用于回测的 1 分钟 parquet 合约列表。"""
    return list_backtest_symbols()


@router.get("/metrics", response_model=list[MetricInfo])
def list_metrics() -> list[MetricInfo]:
    """业务功能: 查询 quant_runtime 当前支持的绩效指标元数据。"""
    return get_metrics()


@router.post("/run", response_model=BacktestRunResponse)
def post_run_backtest(request: BacktestRunRequest) -> BacktestRunResponse:
    """业务功能: 同步执行一次回测并直接返回完整结果。"""
    return run_backtest(request)


@router.post("/jobs", response_model=BacktestJobSubmitResponse)
def post_submit_backtest_job(request: BacktestRunRequest) -> BacktestJobSubmitResponse:
    """业务功能: 提交异步回测任务，避免长耗时请求阻塞 HTTP 调用。"""
    return submit_backtest_job(request)


@router.get("/jobs/{job_id}", response_model=BacktestJobStatusResponse)
def get_backtest_job(job_id: str) -> BacktestJobStatusResponse:
    """业务功能: 查询异步回测任务的当前状态和失败原因。"""
    return get_backtest_job_status(job_id)


@router.get("/jobs/{job_id}/result", response_model=BacktestRunResponse)
def get_backtest_job_result_endpoint(job_id: str) -> BacktestRunResponse:
    """业务功能: 获取已完成异步回测任务的领域结果。"""
    return get_backtest_job_result(job_id)
