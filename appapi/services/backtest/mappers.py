"""Map quant runtime domain payloads to appapi HTTP schemas."""

from typing import Any

from appapi.schemas.backtest import BacktestRunResponse


HTTP_BACKTEST_FIELDS = {
    "symbol",
    "strategy",
    "initial_cash",
    "final_equity",
    "trades",
    "equity_curve",
    "metrics",
}


def to_backtest_run_response(payload: dict[str, Any]) -> BacktestRunResponse:
    http_payload = {key: payload[key] for key in HTTP_BACKTEST_FIELDS if key in payload}
    return BacktestRunResponse.model_validate(http_payload)
