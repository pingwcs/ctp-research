"""API-facing backtest service that delegates execution to quant runtime."""

from appapi.schemas.backtest import BacktestRunRequest, BacktestRunResponse
from appapi.services.backtest.mappers import to_backtest_run_response
from appapi.services.backtest.payloads import build_runner_payload
from appapi.services.backtest.runner_client import invoke_runner
from appapi.services.backtest.validation import validate_backtest_request


def run_backtest(request: BacktestRunRequest) -> BacktestRunResponse:
    validate_backtest_request(request)
    payload = invoke_runner("run", build_runner_payload(request))
    return to_backtest_run_response(payload)
