"""Tests for quant_runtime runner JSON envelopes."""

import json

from quant_runtime import runner
from quant_runtime.contracts import BacktestDomainResult


def test_runner_list_symbols_outputs_json(tmp_path, capsys):
    (tmp_path / "RB0909.parquet").write_text("", encoding="utf-8")

    exit_code = runner.main(["list-symbols", "--minute-data-dir", str(tmp_path)])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {"symbols": ["RB0909"]}


def test_runner_metadata_outputs_json(capsys):
    exit_code = runner.main(["metadata"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert [strategy["id"] for strategy in payload["strategies"]] == ["ma_cross"]


def test_runner_run_accepts_payload_file(tmp_path, capsys, monkeypatch):
    payload_path = tmp_path / "payload.json"
    payload_path.write_bytes(
        b"\xef\xbb\xbf"
        + json.dumps(
            {
                "symbol": "RB0909",
                "strategy": "ma_cross",
                "metrics": ["total_return"],
            },
        ).encode("utf-8"),
    )
    observed = {}

    def fake_run_backtest(request, minute_data_dir):
        observed["request"] = request
        observed["minute_data_dir"] = minute_data_dir
        return BacktestDomainResult(
            symbol=request.symbol,
            strategy=request.strategy,
            engine="test",
            initial_cash=100000.0,
            final_equity=101000.0,
            trades=[],
            equity_curve=[],
            metrics={"total_return": 0.01},
        )

    monkeypatch.setattr(
        "quant_runtime.adapters.vnpy.backtester.run_backtest",
        fake_run_backtest,
    )

    exit_code = runner.main(
        [
            "run",
            "--minute-data-dir",
            str(tmp_path),
            "--payload-file",
            str(payload_path),
        ],
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["symbol"] == "RB0909"
    assert observed["request"].metrics == ["total_return"]
    assert observed["minute_data_dir"] == tmp_path.resolve()


def test_runner_error_outputs_error_json(capsys):
    exit_code = runner.main(["run", "--payload-json", "{}"])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["status_code"] == 500
    assert "symbol" in payload["error"]["detail"]
