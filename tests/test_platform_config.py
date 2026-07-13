from pathlib import Path

from platform_config import load_platform_config


def test_platform_root_sets_single_host_default_directories() -> None:
    root = Path("C:/platform-root")

    config = load_platform_config({"PLATFORM_ROOT": str(root)})

    assert config.data_root == root / "var" / "data"
    assert config.market_data_root == root / "var" / "data" / "market"
    assert config.state_root == root / "var" / "state"
    assert config.private_network_only is True
