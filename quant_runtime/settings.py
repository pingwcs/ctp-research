"""Runtime settings for the standalone quant runtime package."""

from dataclasses import dataclass
import os
from pathlib import Path
import sys


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path.resolve()
    return (_repo_root() / path).resolve()


@dataclass(frozen=True)
class QuantRuntimeSettings:
    repo_root: Path = _repo_root()
    minute_data_dir: Path = _resolve(
        os.getenv("QUANT_RUNTIME_1MIN_DIR", "data/output/1min"),
    )
    runtime_dir: Path = _resolve(
        os.getenv("QUANT_RUNTIME_DIR", "quant_runtime/runtime"),
    )
    database_name: str = os.getenv("QUANT_RUNTIME_DATABASE", "sqlite")

    @property
    def vntrader_dir(self) -> Path:
        return self.runtime_dir / ".vntrader"


settings = QuantRuntimeSettings()


def ensure_runtime_dirs() -> None:
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    settings.vntrader_dir.mkdir(parents=True, exist_ok=True)


def prepare_vnpy_runtime() -> None:
    ensure_runtime_dirs()
    repo_root = str(settings.repo_root)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    os.chdir(settings.runtime_dir)
