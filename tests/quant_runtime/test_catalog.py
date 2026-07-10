"""Tests for quant runtime metadata ownership."""

import json

import pytest

from quant_runtime import catalog
from quant_runtime.catalog import metadata, validate_request_ids
from quant_runtime.contracts import RunnerError


def test_metadata_is_owned_by_quant_runtime():
    data = metadata()

    assert [strategy["id"] for strategy in data["strategies"]] == ["ma_cross"]
    assert {metric["id"] for metric in data["metrics"]} == {
        "annual_return",
        "calmar",
        "profit_factor",
        "max_drawdown",
        "sharpe",
        "sortino",
        "total_return",
        "information_ratio",
        "win_rate",
    }


def test_validate_request_ids_uses_runtime_catalog():
    assert validate_request_ids("ma_cross", ["total_return"]) == ["total_return"]

    with pytest.raises(RunnerError) as exc_info:
        validate_request_ids("ma_cross", ["not_a_metric"])

    assert exc_info.value.status_code == 400
    assert "unsupported metrics" in exc_info.value.detail


def test_metadata_can_be_loaded_from_config_file(tmp_path, monkeypatch):
    config_path = tmp_path / "backtest.json"
    config_path.write_text(
        json.dumps(
            {
                "default_strategy": "config_strategy",
                "engine": {
                    "initial_cash": 50000.0,
                    "contract_size": 2,
                    "rate": 0.0,
                    "slippage": 0.5,
                    "price_tick": 0.2,
                },
                "strategies": [
                    {
                        "id": "config_strategy",
                        "name": "Configured Strategy",
                        "description": "Loaded from JSON.",
                        "engine": "vnpy",
                        "class_path": (
                            "quant_runtime.adapters.vnpy.strategies."
                            "ma_cross_strategy.MaCrossStrategy"
                        ),
                    },
                ],
                "metrics": [
                    {
                        "id": "config_metric",
                        "name": "Configured Metric",
                        "description": "Loaded from JSON.",
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

    data = catalog.metadata()

    assert [strategy["id"] for strategy in data["strategies"]] == ["config_strategy"]
    assert [metric["id"] for metric in data["metrics"]] == ["config_metric"]
    assert catalog.validate_request_ids("config_strategy", []) == ["config_metric"]
