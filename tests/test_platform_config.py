from global_config import load_environment_config
from platform_config import load_platform_config


def test_platform_root_sets_single_host_default_directories(tmp_path) -> None:
    root = tmp_path / "platform-root"

    config = load_platform_config({"PLATFORM_ROOT": str(root)})

    assert config.data_root == root / "var" / "data"
    assert config.market_data_root == root / "var" / "data" / "market"
    assert config.state_root == root / "var" / "state"
    assert config.private_network_only is True


def test_platform_config_defaults_postgres_dsn_to_empty_string() -> None:
    assert load_platform_config({}).postgres_dsn == ""


def test_platform_config_uses_injected_environment_without_process_state(
    monkeypatch,
) -> None:
    monkeypatch.setenv("PLATFORM_POSTGRES_DSN", "postgresql://process-only")

    config = load_platform_config({"PLATFORM_POSTGRES_DSN": "postgresql://injected"})

    assert config.postgres_dsn == "postgresql://injected"


def test_platform_config_allows_explicit_private_network_flag_false() -> None:
    config = load_platform_config({"PLATFORM_PRIVATE_NETWORK_ONLY": "false"})

    assert config.private_network_only is False


def test_legacy_market_directories_override_platform_defaults(tmp_path) -> None:
    project_root = tmp_path / "project"

    config = load_environment_config(
        {
            "CTP_RESEARCH_PROJECT_ROOT": str(project_root),
            "MARKET_DATA_DIR": "legacy-data",
            "MARKET_LOG_DIR": "legacy-logs",
        },
    )

    assert config.market_data_dir == project_root / "legacy-data"
    assert config.market_log_dir == project_root / "legacy-logs"
