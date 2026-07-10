"""Map quant runtime domain payloads to appapi HTTP schemas.

业务功能: 把 quant_runtime 的领域 JSON 裁剪为前端 HTTP 合约字段。
算法要点: 使用白名单字段投影，运行时内部字段如 engine 不泄漏到
BacktestRunResponse。
"""

from typing import Any

from appapi.schemas.backtest import BacktestRunResponse


HTTP_BACKTEST_FIELDS = {
    "symbol",
    "strategy",
    "initial_cash",
    "final_equity",
    "trades",
    "equity_curve",
    "metrics",
}


def to_backtest_run_response(payload: dict[str, Any]) -> BacktestRunResponse:
    """业务功能: 将运行时回测结果转换为 API 响应模型。"""
    http_payload = {key: payload[key] for key in HTTP_BACKTEST_FIELDS if key in payload}
    return BacktestRunResponse.model_validate(http_payload)
