"""Application settings for the market-data API."""

from dataclasses import dataclass
import os
from pathlib import Path


def _resolve_from_app(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path.resolve()
    app_dir = Path(__file__).resolve().parents[1]
    return (app_dir / path).resolve()


@dataclass(frozen=True)
class Settings:
    app_name: str = "Futures K-Line API"
    api_prefix: str = "/api/market"
    data_dir: Path = _resolve_from_app(os.getenv("MARKET_DATA_DIR", "../data/output"))
    log_dir: Path = _resolve_from_app(os.getenv("MARKET_LOG_DIR", "logs"))
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "MARKET_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    )


settings = Settings()
