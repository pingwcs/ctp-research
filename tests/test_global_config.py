"""Tests for project-wide environment configuration."""

from pathlib import Path

from global_config import load_environment_config


def test_load_environment_config_resolves_common_env_items(tmp_path):
    environ = {
        "CTP_RESEARCH_PROJECT_ROOT": str(tmp_path),
        "MARKET_DATA_DIR": "market-output",
        "MARKET_LOG_DIR": "api-logs",
        "MARKET_CORS_ORIGINS": "http://localhost:5173, http://127.0.0.1:5173",
        "QUANT_RUNTIME_1MIN_DIR": "runtime-1min",
        "QUANT_RUNTIME_DIR": "runtime-state",
        "QUANT_RUNTIME_DATABASE": "duckdb",
        "QUANT_RUNTIME_PYTHON": "python-test",
        "QUANT_RUNTIME_MODULE": "custom.runner",
        "QUANT_RUNTIME_TIMEOUT_SECONDS": "9.5",
        "QUANT_RUNTIME_BACKTEST_CONFIG": "config/backtest.json",
    }

    config = load_environment_config(environ)

    assert config.project_root == tmp_path.resolve()
    assert config.market_data_dir == tmp_path / "market-output"
    assert config.market_log_dir == tmp_path / "api-logs"
    assert config.market_cors_origins == (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    assert config.quant_runtime_minute_data_dir == tmp_path / "runtime-1min"
    assert config.quant_runtime_dir == tmp_path / "runtime-state"
    assert config.quant_runtime_database == "duckdb"
    assert config.quant_runtime_python == "python-test"
    assert config.quant_runtime_module == "custom.runner"
    assert config.quant_runtime_timeout_seconds == 9.5
    assert config.quant_runtime_backtest_config == tmp_path / "config" / "backtest.json"


def test_default_environment_config_points_at_repo_root():
    config = load_environment_config({})
    repo_root = Path(__file__).resolve().parents[1]

    assert config.project_root == repo_root
    assert config.market_data_dir == repo_root / "data" / "output"
    assert config.market_log_dir == repo_root / "appapi" / "logs"
    assert config.quant_runtime_minute_data_dir == repo_root / "data" / "output" / "1min"
    assert config.quant_runtime_dir == repo_root / "quant_runtime" / "runtime"
    assert (
        config.quant_runtime_backtest_config
        == repo_root / "quant_runtime" / "config" / "backtest.json"
    )
