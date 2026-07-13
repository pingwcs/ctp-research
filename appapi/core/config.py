"""Application settings for the market-data API.

业务功能: 汇总 appapi 需要的目录、路由前缀、CORS 和 quant_runtime 调用配置。
算法要点: 配置来源集中到 global_config，避免 API、前端代理和运行时使用
不同的路径默认值。
"""

from dataclasses import dataclass
from pathlib import Path

from global_config import load_environment_config


@dataclass(frozen=True)
class Settings:
    """业务功能: appapi 运行所需的不可变配置快照。"""

    app_name: str = "Futures Quantitative Research API"
    project_root: Path = Path()
    market_prefix: str = "/api/market"
    backtest_prefix: str = "/api/backtest"
    auth_prefix: str = "/api/auth"
    trading_prefix: str = "/api/trading"
    data_dir: Path = project_root
    log_dir: Path = project_root
    auth_database_dsn: str = ""
    auth_token_secret: str = ""
    quant_runtime_python: str = ""
    quant_runtime_module: str = ""
    quant_runtime_timeout_seconds: float = 0.0
    quant_runtime_minute_data_dir: Path = project_root
    cors_origins: tuple[str, ...] = ()


def load_settings(environ=None) -> Settings:
    """业务功能: 从环境变量和默认路径装配 appapi 配置。"""
    env_config = load_environment_config(environ)
    return Settings(
        project_root=env_config.project_root,
        data_dir=env_config.market_data_dir,
        log_dir=env_config.market_log_dir,
        auth_database_dsn=env_config.auth_database_dsn,
        auth_token_secret=env_config.auth_token_secret,
        quant_runtime_python=env_config.quant_runtime_python,
        quant_runtime_module=env_config.quant_runtime_module,
        quant_runtime_timeout_seconds=env_config.quant_runtime_timeout_seconds,
        quant_runtime_minute_data_dir=env_config.quant_runtime_minute_data_dir,
        cors_origins=env_config.market_cors_origins,
    )


settings = load_settings()
