"""Single-host configuration shared by local platform services."""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping


ENV_PLATFORM_ROOT = "PLATFORM_ROOT"
ENV_PLATFORM_POSTGRES_DSN = "PLATFORM_POSTGRES_DSN"
ENV_PLATFORM_PRIVATE_NETWORK_ONLY = "PLATFORM_PRIVATE_NETWORK_ONLY"

DEFAULT_PLATFORM_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class PlatformConfig:
    app_environment: str
    data_root: Path
    market_data_root: Path
    state_root: Path
    postgres_dsn: str
    private_network_only: bool


def _is_true(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_platform_config(
    environ: Mapping[str, str] | None = None,
) -> PlatformConfig:
    """Load single-host paths and connection details from an environment mapping."""
    env = os.environ if environ is None else environ
    app_environment = env.get("APP_ENV", "dev")
    root_value = env.get(ENV_PLATFORM_ROOT)
    root = (Path(root_value) if root_value else DEFAULT_PLATFORM_ROOT).expanduser()
    root = root.resolve()
    data_root = root / "var" / "data"
    return PlatformConfig(
        app_environment=app_environment,
        data_root=data_root,
        market_data_root=data_root / "market",
        state_root=root / "var" / "state",
        postgres_dsn=env.get(ENV_PLATFORM_POSTGRES_DSN, ""),
        private_network_only=_is_true(
            env.get(ENV_PLATFORM_PRIVATE_NETWORK_ONLY, "true"),
        ),
    )
