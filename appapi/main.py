"""FastAPI entrypoint."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from appapi.api.market import router as market_router
from appapi.api.backtest import router as backtest_router
from appapi.core.config import settings
from appapi.core.logging import setup_logging


setup_logging()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market_router, prefix=settings.market_prefix, tags=["market"])
app.include_router(backtest_router, prefix=settings.backtest_prefix, tags=["backtest"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
def on_startup() -> None:
    logger.info("{} started; parquet data dir={}", settings.app_name, settings.data_dir)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("appapi.main:app", host="127.0.0.1", port=8000, reload=False)
