"""Application settings for the market-data API."""

from dataclasses import dataclass
from pathlib import Path

from global_config import load_environment_config


@dataclass(frozen=True)
class Settings:
    app_name: str = "Futures Quantitative Research API"
    project_root: Path = Path()
    market_prefix: str = "/api/market"
    backtest_prefix: str = "/api/backtest"
    data_dir: Path = project_root
    log_dir: Path = project_root
    quant_runtime_python: str = ""
    quant_runtime_module: str = ""
    quant_runtime_timeout_seconds: float = 0.0
    quant_runtime_minute_data_dir: Path = project_root
    cors_origins: tuple[str, ...] = ()


def load_settings(environ=None) -> Settings:
    env_config = load_environment_config(environ)
    return Settings(
        project_root=env_config.project_root,
        data_dir=env_config.market_data_dir,
        log_dir=env_config.market_log_dir,
        quant_runtime_python=env_config.quant_runtime_python,
        quant_runtime_module=env_config.quant_runtime_module,
        quant_runtime_timeout_seconds=env_config.quant_runtime_timeout_seconds,
        quant_runtime_minute_data_dir=env_config.quant_runtime_minute_data_dir,
        cors_origins=env_config.market_cors_origins,
    )


settings = load_settings()
