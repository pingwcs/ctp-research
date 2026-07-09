"""Tests for mapping runtime domain results to HTTP DTOs."""

from appapi.services.backtest.mappers import to_backtest_run_response


def test_to_backtest_run_response_drops_runtime_only_fields():
    response = to_backtest_run_response(
        {
            "symbol": "RB0909",
            "strategy": "ma_cross",
            "engine": "vnpy",
            "initial_cash": 100000.0,
            "final_equity": 101000.0,
            "trades": [],
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
        },
    )

    assert response.symbol == "RB0909"
    assert response.final_equity == 101000.0
    assert not hasattr(response, "engine")
