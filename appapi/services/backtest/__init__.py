"""Public backtest service API.

业务功能: 暴露回测服务层的稳定入口，隐藏 catalog、payload 和 runner_client 的
内部拆分。
算法要点: __all__ 明确允许外部导入的服务函数，减少跨模块依赖到实现细节。
"""

from appapi.services.backtest.catalog import (
    available_metric_ids,
    available_strategy_ids,
    get_metrics,
    get_strategies,
    list_backtest_symbols,
)
from appapi.services.backtest.service import (
    get_backtest_job_result,
    get_backtest_job_status,
    run_backtest,
    submit_backtest_job,
)


__all__ = [
    "available_metric_ids",
    "available_strategy_ids",
    "get_metrics",
    "get_strategies",
    "get_backtest_job_result",
    "get_backtest_job_status",
    "list_backtest_symbols",
    "run_backtest",
    "submit_backtest_job",
]
