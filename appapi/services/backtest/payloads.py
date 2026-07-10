"""Build quant-runtime runner payloads from HTTP backtest requests.

业务功能: 把 FastAPI/Pydantic 请求模型转换成 quant_runtime.runner 协议。
算法要点: 只发送用户显式提供的可选字段，让运行时保留默认策略和时间范围
推断逻辑。
"""

from typing import Any

from appapi.schemas.backtest import BacktestRunRequest


def build_runner_payload(request: BacktestRunRequest) -> dict[str, Any]:
    """业务功能: 生成同步或异步回测都可复用的 runner payload。"""
    payload: dict[str, Any] = {
        "symbol": request.symbol,
        "metrics": request.metrics,
    }
    if request.strategy:
        payload["strategy"] = request.strategy
    if request.start_time is not None:
        payload["start_time"] = request.start_time
    if request.end_time is not None:
        payload["end_time"] = request.end_time
    return payload
