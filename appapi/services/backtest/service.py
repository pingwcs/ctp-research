"""API-facing backtest service that delegates execution to quant runtime."""

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
    return RunnerJobClient()


def run_backtest(request: BacktestRunRequest) -> BacktestRunResponse:
    payload = invoke_runner("run", build_runner_payload(request))
    return to_backtest_run_response(payload)


def submit_backtest_job(request: BacktestRunRequest) -> BacktestJobSubmitResponse:
    payload = get_runner_job_client().submit(build_runner_payload(request))
    return BacktestJobSubmitResponse.model_validate(payload)


def get_backtest_job_status(job_id: str) -> BacktestJobStatusResponse:
    payload = get_runner_job_client().status(job_id)
    return BacktestJobStatusResponse.model_validate(payload)


def get_backtest_job_result(job_id: str) -> BacktestRunResponse:
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
