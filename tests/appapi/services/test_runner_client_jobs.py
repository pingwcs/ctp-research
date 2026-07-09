"""Tests for future job-oriented runner client behavior."""

from appapi.services.backtest.runner_client import RunnerJobClient


def test_runner_job_client_can_submit_poll_and_fetch(monkeypatch):
    calls = []

    def fake_invoke(command, payload=None):
        calls.append((command, payload))
        if command == "submit":
            return {"job_id": "job-1", "status": "queued"}
        if command == "status":
            return {"job_id": "job-1", "status": "succeeded"}
        if command == "result":
            return {"job_id": "job-1", "result": {"symbol": "RB0909"}}
        raise AssertionError(command)

    client = RunnerJobClient(invoke=fake_invoke)

    submitted = client.submit({"symbol": "RB0909"})
    status = client.status(submitted["job_id"])
    result = client.result(submitted["job_id"])

    assert status["status"] == "succeeded"
    assert result["result"]["symbol"] == "RB0909"
    assert calls == [
        ("submit", {"symbol": "RB0909"}),
        ("status", {"job_id": "job-1"}),
        ("result", {"job_id": "job-1"}),
    ]
