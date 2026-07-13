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


@pytest.mark.parametrize("command", ["status", "result"])
def test_unrelated_worker_error_does_not_release_an_active_job(
    monkeypatch, command: str
) -> None:
    gate = BacktestConcurrencyGate()
    monkeypatch.setattr(runner, "_backtest_concurrency_gate", gate)
    monkeypatch.setattr(
        runner,
        "_backtest_job_capacity",
        runner.BacktestJobCapacityRegistry(gate),
    )

    class WorkerAdapter:
        def invoke(self, invoked_command, payload):
            if invoked_command == "submit":
                return {"job_id": "job-1", "status": "queued", "error": None}
            if invoked_command == command:
                assert payload == {"job_id": "unrelated-job"}
                return {"error": {"status_code": 404, "detail": "job not found"}}
            raise AssertionError(f"unexpected command: {invoked_command}")

    runner_instance = QuantRuntimeRunner(worker_adapter=WorkerAdapter())
    assert runner_instance.submit({"symbol": "RB0909"})["job_id"] == "job-1"

    with pytest.raises(HTTPException) as exc_info:
        getattr(runner_instance, command)("unrelated-job")

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    with pytest.raises(HTTPException) as exc_info:
        runner_instance.submit({"symbol": "RB0910"})

    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_malformed_submit_status_releases_its_own_reservation(monkeypatch) -> None:
    gate = BacktestConcurrencyGate()
    monkeypatch.setattr(runner, "_backtest_concurrency_gate", gate)
    monkeypatch.setattr(
        runner,
        "_backtest_job_capacity",
        runner.BacktestJobCapacityRegistry(gate),
    )

    class WorkerAdapter:
        def __init__(self) -> None:
            self.submissions = 0

        def invoke(self, command, payload):
            assert command == "submit"
            self.submissions += 1
            if self.submissions == 1:
                return {"job_id": "job-1", "status": "unknown", "error": None}
            return {"job_id": "job-2", "status": "succeeded", "error": None}

    runner_instance = QuantRuntimeRunner(worker_adapter=WorkerAdapter())

    with pytest.raises(HTTPException) as exc_info:
        runner_instance.submit({"symbol": "RB0909"})

    assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY
    assert runner_instance.submit({"symbol": "RB0910"})["job_id"] == "job-2"


def test_malformed_status_releases_only_its_own_reservation(monkeypatch) -> None:
    gate = BacktestConcurrencyGate()
    monkeypatch.setattr(runner, "_backtest_concurrency_gate", gate)
    monkeypatch.setattr(
        runner,
        "_backtest_job_capacity",
        runner.BacktestJobCapacityRegistry(gate),
    )

    class WorkerAdapter:
        def __init__(self) -> None:
            self.submissions = 0

        def invoke(self, command, payload):
            if command == "submit":
                self.submissions += 1
                return {
                    "job_id": f"job-{self.submissions}",
                    "status": "queued",
                    "error": None,
                }
            if command == "status":
                return {"job_id": "job-1", "status": "unknown", "error": None}
            raise AssertionError(f"unexpected command: {command}")

    runner_instance = QuantRuntimeRunner(worker_adapter=WorkerAdapter())
    runner_instance.submit({"symbol": "RB0909"})

    with pytest.raises(HTTPException) as exc_info:
        runner_instance.status("job-1")

    assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY
    assert runner_instance.submit({"symbol": "RB0910"})["job_id"] == "job-2"


@pytest.mark.parametrize("command", ["status", "result"])
@pytest.mark.parametrize("response_job_id", ["other", None, 1])
def test_mismatched_worker_job_id_does_not_release_active_reservation(
    monkeypatch, command: str, response_job_id: str | int | None
) -> None:
    gate = BacktestConcurrencyGate()
    monkeypatch.setattr(runner, "_backtest_concurrency_gate", gate)
    monkeypatch.setattr(
        runner,
        "_backtest_job_capacity",
        runner.BacktestJobCapacityRegistry(gate),
    )

    class WorkerAdapter:
        def invoke(self, invoked_command, payload):
            if invoked_command == "submit":
                return {"job_id": "job-1", "status": "queued", "error": None}
            if invoked_command == command:
                assert payload == {"job_id": "job-1"}
                return {
                    "job_id": response_job_id,
                    "status": "succeeded",
                    "error": None,
                }
            raise AssertionError(f"unexpected command: {invoked_command}")

    runner_instance = QuantRuntimeRunner(worker_adapter=WorkerAdapter())
    runner_instance.submit({"symbol": "RB0909"})

    with pytest.raises(HTTPException) as exc_info:
        getattr(runner_instance, command)("job-1")

    assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY
    with pytest.raises(HTTPException) as exc_info:
        runner_instance.submit({"symbol": "RB0910"})

    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_shutdown_only_releases_reservations_owned_by_that_runner(monkeypatch) -> None:
    gate = BacktestConcurrencyGate()
    monkeypatch.setattr(runner, "_backtest_concurrency_gate", gate)
    monkeypatch.setattr(
        runner,
        "_backtest_job_capacity",
        runner.BacktestJobCapacityRegistry(gate),
    )

    class WorkerAdapter:
        def invoke(self, command, payload):
            assert command == "submit"
            return {"job_id": "job-1", "status": "queued", "error": None}

    active_runner = QuantRuntimeRunner(worker_adapter=WorkerAdapter())
    other_runner = QuantRuntimeRunner(worker_adapter=WorkerAdapter())
    active_runner.submit({"symbol": "RB0909"})

    other_runner.shutdown()

    with pytest.raises(HTTPException) as exc_info:
        other_runner.submit({"symbol": "RB0910"})

    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    active_runner.shutdown()


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
