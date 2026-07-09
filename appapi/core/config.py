"""Application settings for the market-data API."""

from dataclasses import dataclass
import os
from pathlib import Path
import sys


def _resolve_from_app(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path.resolve()
    app_dir = Path(__file__).resolve().parents[1]
    return (app_dir / path).resolve()


@dataclass(frozen=True)
class Settings:
    app_name: str = "Futures Quantitative Research API"
    market_prefix: str = "/api/market"
    backtest_prefix: str = "/api/backtest"
    data_dir: Path = _resolve_from_app(
        os.getenv("MARKET_DATA_DIR", "../data/output"),
    )
    log_dir: Path = _resolve_from_app(os.getenv("MARKET_LOG_DIR", "logs"))
    quant_runtime_python: str = os.getenv("QUANT_RUNTIME_PYTHON", sys.executable)
    quant_runtime_module: str = os.getenv(
        "QUANT_RUNTIME_MODULE",
        "quant_runtime.runner",
    )
    quant_runtime_timeout_seconds: float = float(
        os.getenv("QUANT_RUNTIME_TIMEOUT_SECONDS", "120"),
    )
    quant_runtime_minute_data_dir: Path = _resolve_from_app(
        os.getenv("QUANT_RUNTIME_1MIN_DIR", "../data/output/1min"),
    )
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "MARKET_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    )


settings = Settings()
