"""Run vn.py backtests and return quant runtime domain results.

业务功能: 将 BacktestRequest 转换为 vn.py BacktestingEngine 执行，并返回
quant_runtime 的统一领域结果。
算法要点: 先导入请求范围内的分钟 bar，再设置引擎参数、运行策略、计算统计，
最后从 vn.py daily_df/trades 抽取权益曲线、成交和配置化指标。
"""

from datetime import date, datetime, time
from importlib import import_module
from pathlib import Path

from quant_runtime.adapters.vnpy.database import prepare_symbol_bars
from quant_runtime.backtest_config import EngineConfig
from quant_runtime.backtest_metrics import metric_value
from quant_runtime.catalog import (
    engine_config,
    metric_config,
    strategy_config,
    validate_request_ids,
)
from quant_runtime.contracts import (
    BacktestDomainResult,
    BacktestRequest,
    BacktestTrade,
    EquityPoint,
    RunnerError,
)
from quant_runtime.settings import settings


def _epoch(value: date | datetime) -> int:
    """算法要点: date 按当日零点转换，统一输出 Unix 秒。"""
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, time.min)
    return int(value.timestamp())


def _load_class(class_path: str):
    """业务功能: 按 backtest.json 中的 class_path 动态加载策略类。"""
    module_name, separator, class_name = class_path.rpartition(".")
    if not separator or not module_name or not class_name:
        raise RunnerError(500, f"invalid strategy class path: {class_path}")
    try:
        module = import_module(module_name)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as exc:
        raise RunnerError(500, f"failed to load strategy class: {class_path}") from exc


def _build_equity_curve(
    engine,
    config: EngineConfig,
) -> list[EquityPoint]:
    """业务功能: 从 vn.py daily_df 构造前端需要的权益曲线。

    算法要点: 优先使用 balance；缺失时用 initial_cash + net_pnl 兜底。
    持仓市值按 end_pos * close_price * contract_size 估算，现金为权益减市值。
    """
    daily_df = getattr(engine, "daily_df", None)
    if daily_df is None or daily_df.empty:
        return []

    points: list[EquityPoint] = []
    for index, row in daily_df.iterrows():
        timestamp = index.to_pydatetime() if hasattr(index, "to_pydatetime") else index
        equity = float(
            row.get("balance", row.get("net_pnl", 0.0) + config.initial_cash)
        )
        position = int(row.get("end_pos", 0) or 0)
        close_price = float(row.get("close_price", 0.0) or 0.0)
        position_value = position * close_price * config.contract_size
        points.append(
            EquityPoint(
                time=_epoch(timestamp),
                equity=equity,
                cash=equity - position_value,
                position_value=position_value,
                position=position,
            ),
        )
    return points


def _build_daily_net_pnl(engine) -> list[float]:
    """业务功能: 提取每日净盈亏序列，供 Profit Factor 等指标计算。"""
    daily_df = getattr(engine, "daily_df", None)
    if daily_df is None or daily_df.empty:
        return []
    return [float(row.get("net_pnl", 0.0) or 0.0) for _, row in daily_df.iterrows()]


def _build_trades(engine) -> list[BacktestTrade]:
    """业务功能: 将 vn.py 成交对象转换成通用 BacktestTrade。"""
    from vnpy.trader.constant import Direction

    trades: list[BacktestTrade] = []
    for trade in sorted(engine.trades.values(), key=lambda item: item.datetime):
        side = "buy" if trade.direction == Direction.LONG else "sell"
        trades.append(
            BacktestTrade(
                time=_epoch(trade.datetime),
                side=side,
                price=float(trade.price),
                quantity=int(trade.volume),
                cash=0.0,
                reason=str(getattr(trade, "offset", "")),
            ),
        )
    return trades


def run_backtest(
    request: BacktestRequest,
    minute_data_dir: Path = settings.minute_data_dir,
) -> BacktestDomainResult:
    """业务功能: 执行一次 VNPY 回测并返回领域结果。

    算法要点: 请求未给时间范围时使用导入 bar 的首尾时间；指标列表先通过
    catalog 校验和默认补全，再逐个调用 metric_value 输出。
    """
    selected_metrics = validate_request_ids(request.strategy, request.metrics)
    selected_strategy = strategy_config(request.strategy)
    if selected_strategy.engine != "vnpy":
        raise RunnerError(
            400, f"unsupported strategy engine: {selected_strategy.engine}"
        )
    strategy_class = _load_class(selected_strategy.class_path)
    config = engine_config()
    if (
        request.start_time is not None
        and request.end_time is not None
        and request.start_time > request.end_time
    ):
        raise RunnerError(400, "start_time must be before end_time")

    bars = prepare_symbol_bars(
        request.symbol,
        minute_data_dir,
        request.start_time,
        request.end_time,
    )

    from vnpy.trader.constant import Exchange, Interval
    from vnpy_ctastrategy.backtesting import BacktestingEngine

    start = request.start_time or bars[0].datetime
    end = request.end_time or bars[-1].datetime

    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol=f"{request.symbol}.{Exchange(bars[0].exchange).value}",
        interval=Interval.MINUTE,
        start=start,
        end=end,
        rate=config.rate,
        slippage=config.slippage,
        size=config.contract_size,
        pricetick=config.price_tick,
        capital=config.initial_cash,
    )
    engine.add_strategy(strategy_class, {})
    engine.load_data()
    engine.run_backtesting()
    engine.calculate_result()
    stats = engine.calculate_statistics(output=False)

    equity_curve = _build_equity_curve(engine, config)
    daily_net_pnl = _build_daily_net_pnl(engine)
    trades = _build_trades(engine)
    metrics = {
        metric: metric_value(stats, metric_config(metric), equity_curve, daily_net_pnl)
        for metric in selected_metrics
    }
    final_equity = equity_curve[-1].equity if equity_curve else config.initial_cash
    return BacktestDomainResult(
        symbol=request.symbol,
        strategy=request.strategy,
        engine="vnpy",
        initial_cash=config.initial_cash,
        final_equity=final_equity,
        trades=trades,
        equity_curve=equity_curve,
        metrics=metrics,
    )
