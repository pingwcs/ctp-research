"""Tests for quant runtime domain result contract."""

from quant_runtime.contracts import BacktestDomainResult, EquityPoint


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
