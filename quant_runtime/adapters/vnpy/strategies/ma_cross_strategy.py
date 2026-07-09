"""vn.py CTA moving-average cross strategy."""

from collections import deque

from quant_runtime.settings import prepare_vnpy_runtime

prepare_vnpy_runtime()

from vnpy.trader.object import BarData, TickData
from vnpy_ctastrategy import BarGenerator, CtaTemplate


class MaCrossStrategy(CtaTemplate):
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
        self.write_log("MaCrossStrategy initialized")

    def on_start(self) -> None:
        self.write_log("MaCrossStrategy started")

    def on_stop(self) -> None:
        self.write_log("MaCrossStrategy stopped")

    def on_tick(self, tick: TickData) -> None:
        return None

    def on_bar(self, bar: BarData) -> None:
        if int(self.bar_window) <= 1:
            self.on_window_bar(bar)
            return
        self._bar_generator.update_bar(bar)

    def on_window_bar(self, bar: BarData) -> None:
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
