from datetime import date
from pathlib import Path
import subprocess
import sys

from market_data.partitions import MarketPartition, partition_path


def test_partition_path_uses_canonical_hive_layout(tmp_path):
    partition = MarketPartition("ctp", "SHFE", "rb2410", date(2026, 7, 13))

    path = partition_path(tmp_path, partition)

    assert path == (
        tmp_path
        / "source=ctp"
        / "exchange=SHFE"
        / "instrument=rb2410"
        / "trading_date=2026-07-13"
        / "ticks.parquet"
    )


def test_pipeline_help_includes_market_root_option():
    project_root = Path(__file__).resolve().parents[1]

    completed = subprocess.run(
        [sys.executable, "data_pipeline/run.py", "--help"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "--market-root" in completed.stdout


def test_pipeline_uses_configured_market_root_when_option_is_omitted(
    monkeypatch, tmp_path
):
    pipeline_root = Path(__file__).resolve().parents[1] / "data_pipeline"
    if str(pipeline_root) not in sys.path:
        sys.path.insert(0, str(pipeline_root))
    import run

    configured_root = tmp_path / "configured-market"
    monkeypatch.setattr(run.default_config, "market_root", str(configured_root))
    monkeypatch.setattr(sys, "argv", ["run.py", "--no-influx"])
    captured = {}

    def fake_run_pipeline(config):
        captured["market_root"] = config.market_root
        return {
            "total_contracts": 0,
            "successful": 0,
            "failed": 0,
            "anomalies_count": 0,
            "daily_volume_path": "",
            "quality_log_path": "",
        }

    monkeypatch.setattr(
        run,
        "run_pipeline",
        fake_run_pipeline,
    )

    assert run.main() == 0
    assert captured["market_root"] == str(configured_root)
