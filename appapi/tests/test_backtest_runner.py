"""Tests for the deep quant runtime runner module."""

from appapi.services.backtest.runner import QuantRuntimeRunner


class FakeSyncAdapter:
    def __init__(self):
        self.calls = []

    def invoke(self, command, payload=None):
        self.calls.append((command, payload))
        if command == "metadata":
            return {
                "strategies": [{"id": "ma_cross"}],
                "metrics": [{"id": "total_return"}],
            }
        if command == "list-symbols":
            return {"symbols": ["RB0909", 2405]}
        if command == "run":
            return {"symbol": payload["symbol"], "metrics": {}}
        raise AssertionError(command)


class FakeWorkerAdapter:
    def __init__(self):
        self.calls = []

    def invoke(self, command, payload=None):
        self.calls.append((command, payload))
        if command == "submit":
            return {"job_id": "job-1", "status": "queued"}
        if command == "status":
            return {"job_id": payload["job_id"], "status": "succeeded"}
        if command == "result":
            return {"job_id": payload["job_id"], "status": "succeeded", "result": {}}
        raise AssertionError(command)


def test_runner_caches_metadata_behind_one_interface():
    now = [10.0]
    sync_adapter = FakeSyncAdapter()
    runner = QuantRuntimeRunner(
        sync_adapter=sync_adapter,
        worker_adapter=FakeWorkerAdapter(),
        metadata_ttl_seconds=30.0,
        clock=lambda: now[0],
    )

    first = runner.metadata()
    second = runner.metadata()
    now[0] = 41.0
    third = runner.metadata()

    assert first == second == third
    assert sync_adapter.calls == [("metadata", None), ("metadata", None)]


def test_runner_collapses_sync_runtime_commands():
    sync_adapter = FakeSyncAdapter()
    runner = QuantRuntimeRunner(
        sync_adapter=sync_adapter,
        worker_adapter=FakeWorkerAdapter(),
    )

    symbols = runner.list_symbols()
    result = runner.run({"symbol": "RB0909"})

    assert symbols == ["RB0909", "2405"]
    assert result == {"symbol": "RB0909", "metrics": {}}
    assert sync_adapter.calls == [
        ("list-symbols", None),
        ("run", {"symbol": "RB0909"}),
    ]


def test_runner_collapses_worker_job_commands():
    worker_adapter = FakeWorkerAdapter()
    runner = QuantRuntimeRunner(
        sync_adapter=FakeSyncAdapter(),
        worker_adapter=worker_adapter,
    )

    submitted = runner.submit({"symbol": "RB0909"})
    status = runner.status(submitted["job_id"])
    result = runner.result(submitted["job_id"])

    assert submitted["status"] == "queued"
    assert status["status"] == "succeeded"
    assert result["status"] == "succeeded"
    assert worker_adapter.calls == [
        ("submit", {"symbol": "RB0909"}),
        ("status", {"job_id": "job-1"}),
        ("result", {"job_id": "job-1"}),
    ]
