"""API-facing backtest service that delegates execution to quant runtime.

业务功能: 连接 HTTP schema、runner payload、同步执行和异步任务状态查询。
算法要点: 运行失败时把 quant_runtime 的错误包转换为 HTTP 错误；未完成任务
返回 409，避免前端把排队/运行中状态误认为空结果。
"""

from fastapi import HTTPException, status

from appapi.schemas.backtest import (
    BacktestJobStatusResponse,
    BacktestJobSubmitResponse,
    BacktestRunRequest,
    BacktestRunResponse,
)
from appapi.services.backtest.mappers import to_backtest_run_response
from appapi.services.backtest.payloads import build_runner_payload
from appapi.services.backtest.runner_client import RunnerJobClient, invoke_runner


def get_runner_job_client() -> RunnerJobClient:
    """业务功能: 创建异步回测任务客户端，便于测试替换传输层。"""
    return RunnerJobClient()


def run_backtest(request: BacktestRunRequest) -> BacktestRunResponse:
    """业务功能: 同步调用 runner 执行一次回测。"""
    payload = invoke_runner("run", build_runner_payload(request))
    return to_backtest_run_response(payload)


def submit_backtest_job(request: BacktestRunRequest) -> BacktestJobSubmitResponse:
    """业务功能: 通过长驻 worker 提交异步回测任务。"""
    payload = get_runner_job_client().submit(build_runner_payload(request))
    return BacktestJobSubmitResponse.model_validate(payload)


def get_backtest_job_status(job_id: str) -> BacktestJobStatusResponse:
    """业务功能: 查询长驻 worker 中的异步任务状态。"""
    payload = get_runner_job_client().status(job_id)
    return BacktestJobStatusResponse.model_validate(payload)


def get_backtest_job_result(job_id: str) -> BacktestRunResponse:
    """业务功能: 读取异步任务结果，并把未完成或失败状态映射成 HTTP 语义。"""
    payload = get_runner_job_client().result(job_id)
    if payload.get("status") != "succeeded":
        error = payload.get("error")
        if isinstance(error, dict):
            raise HTTPException(
                status_code=int(error.get("status_code") or 500),
                detail=str(error.get("detail") or "quant runtime job failed"),
            )
        if error:
            raise HTTPException(status_code=500, detail=str(error))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"backtest job is {payload.get('status') or 'not ready'}",
        )

    result = payload.get("result")
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="quant runtime job returned invalid result",
        )
    return to_backtest_run_response(result)
