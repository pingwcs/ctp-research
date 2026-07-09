"""Tests for appapi backtest orchestration behavior."""

from datetime import datetime

import pytest
from fastapi import HTTPException, status

from appapi.schemas.backtest import BacktestRunRequest
from appapi.services.backtest import (
    get_metrics,
    get_strategies,
    list_backtest_symbols,
    run_backtest,
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


def test_run_backtest_rejects_unsupported_strategy():
    request = BacktestRunRequest(symbol="RB0909", strategy="unknown")

    with pytest.raises(HTTPException) as exc_info:
        run_backtest(request)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


def test_run_backtest_rejects_inverted_time_range():
    request = BacktestRunRequest(
        symbol="RB0909",
        start_time=datetime(2010, 1, 2),
        end_time=datetime(2010, 1, 1),
    )

    with pytest.raises(HTTPException) as exc_info:
        run_backtest(request)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


def test_run_backtest_rejects_unknown_metric_id():
    request = BacktestRunRequest(symbol="RB0909", metrics=["not_a_metric"])

    with pytest.raises(HTTPException) as exc_info:
        run_backtest(request)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
