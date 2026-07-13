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


def test_submit_holds_capacity_until_worker_reports_terminal_status() -> None:
    class WorkerAdapter:
        def __init__(self) -> None:
            self.statuses = {"job-1": "running"}
            self.next_job = 1

        def invoke(self, command, payload):
            if command == "submit":
                job_id = f"job-{self.next_job}"
                self.next_job += 1
                self.statuses[job_id] = "queued"
                return {"job_id": job_id, "status": "queued", "error": None}
            if command == "status":
                job_id = payload["job_id"]
                return {"job_id": job_id, "status": self.statuses[job_id], "error": None}
            raise AssertionError(f"unexpected command: {command}")

    class SyncAdapter:
        def invoke(self, command, payload):
            pytest.fail("sync run must not start while an async job owns capacity")

    worker = WorkerAdapter()
    runner_instance = QuantRuntimeRunner(
        sync_adapter=SyncAdapter(),
        worker_adapter=worker,
    )

    assert runner_instance.submit({"symbol": "RB0909"})["job_id"] == "job-1"

    with pytest.raises(HTTPException) as exc_info:
        runner_instance.submit({"symbol": "RB0910"})

    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    with pytest.raises(HTTPException) as exc_info:
        runner_instance.run({"symbol": "RB0910"})

    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    worker.statuses["job-1"] = "succeeded"
    assert runner_instance.status("job-1")["status"] == "succeeded"

    assert runner_instance.submit({"symbol": "RB0910"})["job_id"] == "job-2"
    worker.statuses["job-2"] = "succeeded"
    runner_instance.status("job-2")


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
