"""Tests for backtest service behavior."""

from datetime import datetime

import pytest
from fastapi import HTTPException, status

from appapi.schemas.backtest import BacktestRunRequest
from appapi.services.backtest import (
    METRICS,
    STRATEGIES,
    list_backtest_symbols,
    run_backtest,
)
from appapi.services.backtest.metrics import fallback_metrics, selected_metrics


def test_backtest_catalog_exports_current_strategy_and_metric_ids():
    assert [strategy.id for strategy in STRATEGIES] == ["ma_cross"]
    assert {metric.id for metric in METRICS} == {
        "annual_return",
        "max_drawdown",
        "sharpe",
        "total_return",
        "win_rate",
    }
    assert "RB0909" in list_backtest_symbols()


def test_run_backtest_matches_current_rb0909_baseline():
    request = BacktestRunRequest(
        symbol="RB0909",
        metrics=["total_return", "max_drawdown"],
    )

    response = run_backtest(request)

    assert response.symbol == "RB0909"
    assert response.strategy == "ma_cross"
    assert response.initial_cash == 100_000.0
    assert response.final_equity == pytest.approx(102_915.0)
    assert len(response.trades) == 310
    assert len(response.equity_curve) == 5355
    assert response.metrics["total_return"] == pytest.approx(0.02915)
    assert response.metrics["max_drawdown"] == pytest.approx(
        -0.060334358993088255,
    )


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


def test_selected_metrics_rejects_unknown_metric_id():
    with pytest.raises(HTTPException) as exc_info:
        selected_metrics(["not_a_metric"], [], [])

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


def test_fallback_metrics_returns_null_values_for_empty_curve():
    values = fallback_metrics([], [])

    assert values == {
        "annual_return": None,
        "max_drawdown": None,
        "sharpe": None,
        "total_return": None,
        "win_rate": None,
    }
