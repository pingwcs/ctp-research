"""Runtime settings for the standalone quant runtime package."""

from dataclasses import dataclass
import os
from pathlib import Path
import sys

from global_config import load_environment_config


@dataclass(frozen=True)
class QuantRuntimeSettings:
    repo_root: Path
    minute_data_dir: Path
    runtime_dir: Path
    database_name: str

    @property
    def vntrader_dir(self) -> Path:
        return self.runtime_dir / ".vntrader"


def load_settings(environ=None) -> QuantRuntimeSettings:
    env_config = load_environment_config(environ)
    return QuantRuntimeSettings(
        repo_root=env_config.project_root,
        minute_data_dir=env_config.quant_runtime_minute_data_dir,
        runtime_dir=env_config.quant_runtime_dir,
        database_name=env_config.quant_runtime_database,
    )


settings = load_settings()


def ensure_runtime_dirs() -> None:
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    settings.vntrader_dir.mkdir(parents=True, exist_ok=True)


def prepare_vnpy_runtime() -> None:
    ensure_runtime_dirs()
    repo_root = str(settings.repo_root)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    os.chdir(settings.runtime_dir)
