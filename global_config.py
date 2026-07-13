"""Project-wide environment configuration.

This module is the single place that reads process environment values shared by
the API and quant runtime packages.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Mapping

from platform_config import load_platform_config


DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent

ENV_PROJECT_ROOT = "CTP_RESEARCH_PROJECT_ROOT"
ENV_MARKET_DATA_DIR = "MARKET_DATA_DIR"
ENV_MARKET_LOG_DIR = "MARKET_LOG_DIR"
ENV_MARKET_CORS_ORIGINS = "MARKET_CORS_ORIGINS"
ENV_AUTH_TOKEN_SECRET = "AUTH_TOKEN_SECRET"
ENV_QUANT_RUNTIME_1MIN_DIR = "QUANT_RUNTIME_1MIN_DIR"
ENV_QUANT_RUNTIME_DIR = "QUANT_RUNTIME_DIR"
ENV_QUANT_RUNTIME_DATABASE = "QUANT_RUNTIME_DATABASE"
ENV_QUANT_RUNTIME_PYTHON = "QUANT_RUNTIME_PYTHON"
ENV_QUANT_RUNTIME_MODULE = "QUANT_RUNTIME_MODULE"
ENV_QUANT_RUNTIME_TIMEOUT_SECONDS = "QUANT_RUNTIME_TIMEOUT_SECONDS"
ENV_QUANT_RUNTIME_BACKTEST_CONFIG = "QUANT_RUNTIME_BACKTEST_CONFIG"

DEFAULT_MARKET_DATA_DIR = "data/output"
DEFAULT_MARKET_LOG_DIR = "appapi/logs"
DEFAULT_MARKET_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)
DEFAULT_AUTH_TOKEN_SECRET = "local-development-auth-secret"
DEFAULT_QUANT_RUNTIME_1MIN_DIR = "data/output/1min"
DEFAULT_QUANT_RUNTIME_DIR = "quant_runtime/runtime"
DEFAULT_QUANT_RUNTIME_DATABASE = "sqlite"
DEFAULT_QUANT_RUNTIME_MODULE = "quant_runtime.runner"
DEFAULT_QUANT_RUNTIME_TIMEOUT_SECONDS = 120.0
DEFAULT_QUANT_RUNTIME_BACKTEST_CONFIG = "quant_runtime/config/backtest.json"
DEFAULT_QUANT_RUNTIME_BACKTEST_CONFIG_PATH = (
    DEFAULT_PROJECT_ROOT / DEFAULT_QUANT_RUNTIME_BACKTEST_CONFIG
)


@dataclass(frozen=True)
class EnvironmentConfig:
    project_root: Path
    market_data_dir: Path
    market_log_dir: Path
    market_cors_origins: tuple[str, ...]
    auth_database_dsn: str
    auth_token_secret: str
    quant_runtime_minute_data_dir: Path
    quant_runtime_dir: Path
    quant_runtime_database: str
    quant_runtime_python: str
    quant_runtime_module: str
    quant_runtime_timeout_seconds: float
    quant_runtime_backtest_config: Path


def _resolve_project_root(environ: Mapping[str, str]) -> Path:
    value = environ.get(ENV_PROJECT_ROOT)
    if not value:
        return DEFAULT_PROJECT_ROOT

    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (DEFAULT_PROJECT_ROOT / path).resolve()


def _resolve_path(project_root: Path, path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path.resolve()
    return (project_root / path).resolve()


def _csv_tuple(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def load_environment_config(
    environ: Mapping[str, str] | None = None,
) -> EnvironmentConfig:
    env = os.environ if environ is None else environ
    platform_config = load_platform_config(env)
    project_root = _resolve_project_root(env)
    cors_origins = _csv_tuple(
        env.get(
            ENV_MARKET_CORS_ORIGINS,
            ",".join(DEFAULT_MARKET_CORS_ORIGINS),
        ),
    )

    return EnvironmentConfig(
        project_root=project_root,
        market_data_dir=(
            _resolve_path(project_root, env[ENV_MARKET_DATA_DIR])
            if env.get(ENV_MARKET_DATA_DIR)
            else platform_config.market_data_root
        ),
        market_log_dir=(
            _resolve_path(project_root, env[ENV_MARKET_LOG_DIR])
            if env.get(ENV_MARKET_LOG_DIR)
            else platform_config.state_root
        ),
        market_cors_origins=cors_origins,
        auth_database_dsn=platform_config.postgres_dsn,
        auth_token_secret=env.get(
            ENV_AUTH_TOKEN_SECRET,
            DEFAULT_AUTH_TOKEN_SECRET,
        ),
        quant_runtime_minute_data_dir=_resolve_path(
            project_root,
            env.get(ENV_QUANT_RUNTIME_1MIN_DIR, DEFAULT_QUANT_RUNTIME_1MIN_DIR),
        ),
        quant_runtime_dir=_resolve_path(
            project_root,
            env.get(ENV_QUANT_RUNTIME_DIR, DEFAULT_QUANT_RUNTIME_DIR),
        ),
        quant_runtime_database=env.get(
            ENV_QUANT_RUNTIME_DATABASE,
            DEFAULT_QUANT_RUNTIME_DATABASE,
        ),
        quant_runtime_python=env.get(ENV_QUANT_RUNTIME_PYTHON, sys.executable),
        quant_runtime_module=env.get(
            ENV_QUANT_RUNTIME_MODULE,
            DEFAULT_QUANT_RUNTIME_MODULE,
        ),
        quant_runtime_timeout_seconds=float(
            env.get(
                ENV_QUANT_RUNTIME_TIMEOUT_SECONDS,
                str(DEFAULT_QUANT_RUNTIME_TIMEOUT_SECONDS),
            ),
        ),
        quant_runtime_backtest_config=_resolve_path(
            project_root,
            env.get(
                ENV_QUANT_RUNTIME_BACKTEST_CONFIG,
                DEFAULT_QUANT_RUNTIME_BACKTEST_CONFIG,
            ),
        ),
    )
