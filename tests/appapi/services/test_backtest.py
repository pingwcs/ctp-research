"""Tests for appapi backtest orchestration behavior."""

from datetime import datetime

import pytest
from fastapi import HTTPException, status

from appapi.schemas.backtest import BacktestRunRequest
from appapi.services.backtest import (
    get_backtest_job_result,
    get_backtest_job_status,
    get_metrics,
    get_strategies,
    list_backtest_symbols,
    run_backtest,
    submit_backtest_job,
)


def test_backtest_catalog_forwards_runtime_metadata(monkeypatch):
    def fake_metadata(command, payload=None):
        if command == "metadata":
            return {
                "strategies": [
                    {
                        "id": "ma_cross",
                        "name": "MA Cross",
                        "description": "Runtime-owned strategy.",
                        "engine": "vnpy",
                    },
                ],
                "metrics": [
                    {
                        "id": "total_return",
                        "name": "Total Return",
                        "description": "Total equity return.",
                    },
                ],
            }
        return {"symbols": ["RB0909"]}

    monkeypatch.setattr(
        "appapi.services.backtest.metadata_cache.invoke_runner",
        fake_metadata,
    )
    monkeypatch.setattr(
        "appapi.services.backtest.catalog.invoke_runner",
        fake_metadata,
    )

    assert [strategy.id for strategy in get_strategies()] == ["ma_cross"]
    assert [metric.id for metric in get_metrics()] == ["total_return"]
    assert list_backtest_symbols() == ["RB0909"]


def test_run_backtest_forwards_runner_response(monkeypatch):
    def fake_invoke(command, payload):
        assert command == "run"
        assert payload["symbol"] == "RB0909"
        return {
            "symbol": "RB0909",
            "strategy": "ma_cross",
            "initial_cash": 100000.0,
            "final_equity": 101000.0,
            "trades": [
                {
                    "time": 1253026200,
                    "side": "buy",
                    "price": 3660.0,
                    "quantity": 1,
                    "cash": 0.0,
                    "reason": "Offset.OPEN",
                },
            ],
            "equity_curve": [
                {
                    "time": 1253026200,
                    "equity": 101000.0,
                    "cash": 101000.0,
                    "position_value": 0.0,
                    "position": 0,
                },
            ],
            "metrics": {"total_return": 0.01},
        }

    monkeypatch.setattr("appapi.services.backtest.service.invoke_runner", fake_invoke)

    response = run_backtest(
        BacktestRunRequest(symbol="RB0909", metrics=["total_return"]),
    )

    assert response.symbol == "RB0909"
    assert response.final_equity == 101000.0
    assert response.metrics == {"total_return": 0.01}


def test_run_backtest_omits_empty_time_bounds_from_runner_payload(monkeypatch):
    observed = {}

    def fake_invoke(command, payload):
        observed["command"] = command
        observed["payload"] = payload
        return {
            "symbol": "RB0909",
            "strategy": "ma_cross",
            "initial_cash": 100000.0,
            "final_equity": 100000.0,
            "trades": [],
            "equity_curve": [],
            "metrics": {"total_return": 0.0},
        }

    monkeypatch.setattr("appapi.services.backtest.service.invoke_runner", fake_invoke)

    response = run_backtest(
        BacktestRunRequest(symbol="RB0909", metrics=["total_return"]),
    )

    assert response.symbol == "RB0909"
    assert observed["command"] == "run"
    assert "strategy" not in observed["payload"]
    assert "start_time" not in observed["payload"]
    assert "end_time" not in observed["payload"]


def test_run_backtest_leaves_metadata_validation_to_runtime(monkeypatch):
    observed = {}

    def fail_metadata_lookup():
        raise AssertionError("appapi should not consult runtime metadata before run")

    def fake_invoke(command, payload):
        observed["command"] = command
        observed["payload"] = payload
        return {
            "symbol": "RB0909",
            "strategy": "unknown",
            "initial_cash": 100000.0,
            "final_equity": 100000.0,
            "trades": [],
            "equity_curve": [],
            "metrics": {"not_a_metric": None},
        }

    monkeypatch.setattr(
        "appapi.services.backtest.metadata_cache.invoke_runner",
        lambda command, payload=None: fail_metadata_lookup(),
    )
    monkeypatch.setattr("appapi.services.backtest.service.invoke_runner", fake_invoke)

    response = run_backtest(
        BacktestRunRequest(
            symbol="RB0909",
            strategy="unknown",
            metrics=["not_a_metric"],
        ),
    )

    assert response.strategy == "unknown"
    assert observed["command"] == "run"
    assert observed["payload"]["strategy"] == "unknown"


def test_submit_status_and_fetch_backtest_job(monkeypatch):
    calls = []

    class FakeJobClient:
        def submit(self, payload):
            calls.append(("submit", payload))
            return {"job_id": "job-1", "status": "queued"}

        def status(self, job_id):
            calls.append(("status", job_id))
            return {"job_id": job_id, "status": "succeeded", "error": None}

        def result(self, job_id):
            calls.append(("result", job_id))
            return {
                "job_id": job_id,
                "status": "succeeded",
                "result": {
                    "symbol": "RB0909",
                    "strategy": "ma_cross",
                    "initial_cash": 100000.0,
                    "final_equity": 101000.0,
                    "trades": [],
                    "equity_curve": [],
                    "metrics": {"total_return": 0.01},
                },
            }

    monkeypatch.setattr(
        "appapi.services.backtest.service.get_runner_job_client",
        lambda: FakeJobClient(),
    )

    submitted = submit_backtest_job(
        BacktestRunRequest(symbol="RB0909", metrics=["total_return"]),
    )
    status_response = get_backtest_job_status(submitted.job_id)
    result_response = get_backtest_job_result(submitted.job_id)

    assert submitted.status == "queued"
    assert status_response.status == "succeeded"
    assert result_response.final_equity == 101000.0
    assert calls == [
        ("submit", {"symbol": "RB0909", "metrics": ["total_return"]}),
        ("status", "job-1"),
        ("result", "job-1"),
    ]


def test_backtest_job_result_maps_failed_runtime_error(monkeypatch):
    class FakeJobClient:
        def result(self, job_id):
            return {
                "job_id": job_id,
                "status": "failed",
                "error": {"status_code": 400, "detail": "unsupported strategy: bad"},
            }

    monkeypatch.setattr(
        "appapi.services.backtest.service.get_runner_job_client",
        lambda: FakeJobClient(),
    )

    with pytest.raises(HTTPException) as exc_info:
        get_backtest_job_result("job-1")

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "unsupported strategy: bad"
