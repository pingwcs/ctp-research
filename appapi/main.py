"""FastAPI entrypoint.

业务功能: 装配行情接口、回测接口、CORS 和健康检查，作为前端访问
appapi 的统一 HTTP 入口。
算法要点: 入口层不处理行情计算或回测算法，只负责路由注册和启动日志，
把业务处理委托给 api/services 模块。
"""

from pathlib import Path
import sys

if __package__ in (None, ""):
    # 允许直接执行 `python appapi/main.py` 时仍能按包路径导入项目模块。
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from appapi.api.auth import router as auth_router
from appapi.api.backtest import router as backtest_router
from appapi.api.market import router as market_router
from appapi.api.trading import router as trading_router
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

app.include_router(
    market_router,
    prefix=settings.market_prefix,
    tags=["market"],
)
app.include_router(
    backtest_router,
    prefix=settings.backtest_prefix,
    tags=["backtest"],
)
app.include_router(
    auth_router,
    prefix=settings.auth_prefix,
    tags=["auth"],
)
app.include_router(
    trading_router,
    prefix=settings.trading_prefix,
    tags=["trading"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """业务功能: 给部署、代理和本地调试提供轻量存活检查。"""
    return {"status": "ok"}


@app.on_event("startup")
def on_startup() -> None:
    """业务功能: 启动时记录服务名和行情数据目录，便于定位运行环境。"""
    logger.info(
        "{} started; parquet data dir={}",
        settings.app_name,
        settings.data_dir,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("appapi.main:app", host="127.0.0.1", port=8000, reload=False)
