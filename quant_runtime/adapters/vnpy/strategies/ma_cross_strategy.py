"""vn.py CTA moving-average cross strategy.

业务功能: 提供一个默认的 CTA 均线交叉策略，作为 quant_runtime 的可运行
示例策略。
算法要点: 用 bar_window 聚合分钟 bar，计算 fast/slow 简单移动平均；快线
上穿慢线开多，快线下穿慢线平多，并用入场价百分比回撤做止损。
"""

from collections import deque

from quant_runtime.settings import prepare_vnpy_runtime

prepare_vnpy_runtime()

from vnpy.trader.object import BarData, TickData
from vnpy_ctastrategy import BarGenerator, CtaTemplate


class MaCrossStrategy(CtaTemplate):
    """业务功能: VNPY CTA 策略类，由 backtest.json 的 class_path 动态加载。

    算法要点: trend_state 记录上一窗口快慢线关系，只在状态从空头/弱势切到
    多头/强势时买入，从多头/强势切到空头/弱势时卖出，避免每根 bar 重复下单。
    """

    author = "FutureData"

    fast_window = 5
    slow_window = 20
    bar_window = 5
    fixed_size = 1
    stop_loss_pct = 0.10
    price_add = 1.0

    parameters = [
        "fast_window",
        "slow_window",
        "bar_window",
        "fixed_size",
        "stop_loss_pct",
        "price_add",
    ]
    variables = ["fast_ma", "slow_ma", "entry_price", "trend_state"]

    def __init__(self, cta_engine, strategy_name: str, vt_symbol: str, setting: dict):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.fast_ma = 0.0
        self.slow_ma = 0.0
        self.entry_price = 0.0
        self.trend_state = 0
        self._closes = deque(maxlen=max(self.fast_window, self.slow_window))
        self._bar_generator = BarGenerator(
            on_bar=self.on_window_bar,
            window=max(1, int(self.bar_window)),
            on_window_bar=self.on_window_bar,
        )

    def on_init(self) -> None:
        """业务功能: VNPY 策略初始化回调。"""
        self.write_log("MaCrossStrategy initialized")

    def on_start(self) -> None:
        """业务功能: VNPY 策略启动回调。"""
        self.write_log("MaCrossStrategy started")

    def on_stop(self) -> None:
        """业务功能: VNPY 策略停止回调。"""
        self.write_log("MaCrossStrategy stopped")

    def on_tick(self, tick: TickData) -> None:
        """业务功能: 当前策略只基于 bar 回测，tick 回调不产生交易。"""
        return None

    def on_bar(self, bar: BarData) -> None:
        """业务功能: 接收原始分钟 bar，并按 bar_window 聚合后进入信号逻辑。"""
        if int(self.bar_window) <= 1:
            self.on_window_bar(bar)
            return
        self._bar_generator.update_bar(bar)

    def on_window_bar(self, bar: BarData) -> None:
        """算法要点: 在聚合窗口收盘价上计算均线、止损和交叉信号。"""
        self._closes.append(float(bar.close_price))
        if len(self._closes) < self.slow_window:
            return

        values = list(self._closes)
        self.fast_ma = sum(values[-self.fast_window :]) / self.fast_window
        self.slow_ma = sum(values[-self.slow_window :]) / self.slow_window
        current_state = 1 if self.fast_ma >= self.slow_ma else -1

        if self.pos > 0 and self.entry_price > 0:
            drawdown = (self.entry_price - bar.close_price) / self.entry_price
            if drawdown >= self.stop_loss_pct:
                # 止损优先于趋势反转，避免亏损扩大时继续等待均线状态切换。
                self.sell(bar.close_price - self.price_add, abs(self.pos))
                self.trend_state = current_state
                return

        if self.trend_state == -1 and current_state == 1 and self.pos <= 0:
            price = bar.close_price + self.price_add
            self.buy(price, self.fixed_size)
            self.entry_price = price
        elif self.trend_state == 1 and current_state == -1 and self.pos > 0:
            self.sell(bar.close_price - self.price_add, abs(self.pos))
            self.entry_price = 0.0

        self.trend_state = current_state
