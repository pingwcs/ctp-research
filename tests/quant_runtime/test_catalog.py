"""Tests for quant runtime metadata ownership."""

import pytest

from quant_runtime.catalog import metadata, validate_request_ids
from quant_runtime.contracts import RunnerError


def test_metadata_is_owned_by_quant_runtime():
    data = metadata()

    assert [strategy["id"] for strategy in data["strategies"]] == ["ma_cross"]
    assert {metric["id"] for metric in data["metrics"]} == {
        "annual_return",
        "max_drawdown",
        "sharpe",
        "total_return",
        "win_rate",
    }


def test_validate_request_ids_uses_runtime_catalog():
    assert validate_request_ids("ma_cross", ["total_return"]) == ["total_return"]

    with pytest.raises(RunnerError) as exc_info:
        validate_request_ids("ma_cross", ["not_a_metric"])

    assert exc_info.value.status_code == 400
    assert "unsupported metrics" in exc_info.value.detail
