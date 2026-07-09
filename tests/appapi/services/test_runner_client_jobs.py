"""Tests for future job-oriented runner client behavior."""

import json
from pathlib import Path
from types import SimpleNamespace

from appapi.services.backtest import runner_client
from appapi.services.backtest.runner_client import RunnerJobClient
from appapi.services.backtest.runner_client import invoke_runner
from appapi.services.backtest.runner_client import settings


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


def test_invoke_runner_passes_payload_as_cli_args(monkeypatch):
    observed = {}

    def fake_run(args, **kwargs):
        observed["args"] = args
        observed["kwargs"] = kwargs

        class Completed:
            returncode = 0
            stdout = json.dumps({"symbol": "RB0909"})
            stderr = ""

        return Completed()

    monkeypatch.setattr("subprocess.run", fake_run)

    payload = {
        "symbol": "RB0909",
        "strategy": "ma_cross",
        "metrics": ["total_return", "max_drawdown"],
    }

    output = invoke_runner("run", payload)

    assert output == {"symbol": "RB0909"}
    args = observed["args"]
    assert observed["kwargs"]["cwd"] == Path(__file__).resolve().parents[3]
    assert "--payload-json" not in args
    assert args[args.index("--symbol") + 1] == "RB0909"
    assert args[args.index("--strategy") + 1] == "ma_cross"
    assert [
        args[index + 1]
        for index, value in enumerate(args)
        if value == "--metric"
    ] == ["total_return", "max_drawdown"]


def test_invoke_runner_uses_configured_project_root(monkeypatch, tmp_path):
    observed = {}

    def fake_run(args, **kwargs):
        observed["kwargs"] = kwargs

        class Completed:
            returncode = 0
            stdout = json.dumps({"symbol": "RB0909"})
            stderr = ""

        return Completed()

    fake_settings = SimpleNamespace(
        project_root=tmp_path,
        quant_runtime_minute_data_dir=tmp_path / "data",
        quant_runtime_module="quant_runtime.runner",
        quant_runtime_python="python",
        quant_runtime_timeout_seconds=10.0,
    )
    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr(runner_client, "settings", fake_settings)

    output = invoke_runner("run", {"symbol": "RB0909"})

    assert output == {"symbol": "RB0909"}
    assert observed["kwargs"]["cwd"] == tmp_path


def test_runner_module_defaults_to_repo_root_package():
    assert settings.quant_runtime_module == "quant_runtime.runner"
