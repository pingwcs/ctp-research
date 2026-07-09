"""Tests for quant runtime domain result contract."""

from datetime import datetime, timedelta, timezone
import json

from quant_runtime import catalog
from quant_runtime.contracts import BacktestDomainResult, BacktestRequest, EquityPoint


def test_domain_result_includes_engine_without_being_http_dto():
    result = BacktestDomainResult(
        symbol="RB0909",
        strategy="ma_cross",
        engine="vnpy",
        initial_cash=100000.0,
        final_equity=101000.0,
        trades=[],
        equity_curve=[
            EquityPoint(
                time=1253026200,
                equity=101000.0,
                cash=101000.0,
                position_value=0.0,
                position=0,
            ),
        ],
        metrics={"total_return": 0.01},
    )

    payload = result.to_jsonable()

    assert payload["engine"] == "vnpy"
    assert payload["final_equity"] == 101000.0


def test_backtest_request_treats_naive_payload_times_as_chart_timezone():
    request = BacktestRequest.from_payload(
        {
            "symbol": "RB0909",
            "start_time": "2009-04-01T09:00",
            "end_time": "2009-12-31T15:00",
        },
    )

    shanghai = timezone(timedelta(hours=8))
    assert request.start_time == datetime(2009, 4, 1, 9, 0, tzinfo=shanghai)
    assert request.end_time == datetime(2009, 12, 31, 15, 0, tzinfo=shanghai)


def test_backtest_request_uses_configured_default_strategy(tmp_path, monkeypatch):
    config_path = tmp_path / "backtest.json"
    config_path.write_text(
        json.dumps(
            {
                "default_strategy": "configured_default",
                "engine": {
                    "initial_cash": 100000.0,
                    "contract_size": 1,
                    "rate": 0.0,
                    "slippage": 1.0,
                    "price_tick": 1.0,
                },
                "strategies": [
                    {
                        "id": "configured_default",
                        "name": "Configured Default",
                        "description": "Default loaded from config.",
                        "engine": "vnpy",
                        "class_path": (
                            "quant_runtime.adapters.vnpy.strategies."
                            "ma_cross_strategy.MaCrossStrategy"
                        ),
                    },
                ],
                "metrics": [
                    {
                        "id": "total_return",
                        "name": "Total Return",
                        "description": "Total equity return.",
                        "stats_key": "total_return",
                        "divisor": 100.0,
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("QUANT_RUNTIME_BACKTEST_CONFIG", str(config_path))
    if hasattr(catalog, "clear_catalog_cache"):
        catalog.clear_catalog_cache()

    request = BacktestRequest.from_payload({"symbol": "RB0909"})

    assert request.strategy == "configured_default"
