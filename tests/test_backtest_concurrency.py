import pytest
from fastapi import HTTPException, status

from appapi.api import backtest as backtest_api
from appapi.schemas.backtest import BacktestRunRequest
from appapi.services.backtest import runner
from appapi.services.backtest.runner import BacktestConcurrencyGate, QuantRuntimeRunner


def test_backtest_gate_rejects_a_second_active_job() -> None:
    gate = BacktestConcurrencyGate()

    with gate.acquire():
        with pytest.raises(RuntimeError, match="backtest capacity exhausted"):
            with gate.acquire():
                pass


def test_runner_translates_exhausted_capacity_to_http_429(monkeypatch) -> None:
    gate = BacktestConcurrencyGate()
    monkeypatch.setattr(runner, "_backtest_concurrency_gate", gate)

    class Adapter:
        def invoke(self, command, payload):
            return {"command": command, "payload": payload}

    with gate.acquire(), pytest.raises(HTTPException) as exc_info:
        QuantRuntimeRunner(sync_adapter=Adapter()).run({"symbol": "RB0909"})

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "backtest capacity exhausted"


def test_run_endpoint_returns_429_when_backtest_capacity_is_exhausted(monkeypatch) -> None:
    def exhausted(_request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="backtest capacity exhausted",
        )

    monkeypatch.setattr(backtest_api, "run_backtest", exhausted)

    with pytest.raises(HTTPException) as exc_info:
        backtest_api.post_run_backtest(BacktestRunRequest(symbol="RB0909"))

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "backtest capacity exhausted"
