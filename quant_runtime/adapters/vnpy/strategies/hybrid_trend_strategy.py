"""vn.py CTA adapter for the hybrid trend strategy."""

from calendar import monthrange
from datetime import date
import re

from quant_runtime.settings import prepare_vnpy_runtime
from quant_runtime.strategies.hybrid_trend import (
    ContractCandidate,
    ContractSelector,
    HybridBar,
    HybridRiskManager,
    HybridTrendModel,
    TrendDecision,
)

prepare_vnpy_runtime()

from vnpy.trader.object import BarData, TickData
from vnpy_ctastrategy import BarGenerator, CtaTemplate


EXPIRY_SUFFIX_PATTERN = re.compile(r"(\d{4})$")


class HybridTrendStrategy(CtaTemplate):
    """VNPY adapter for hybrid trend following with contract scoring."""

    author = "FutureData"

    fast_window = 50
    slow_window = 200
    adx_window = 14
    adx_min = 25.0
    exit_adx = 20.0
    allow_short = True
    bar_window = 5

    min_days_to_expiry = 30
    max_days_to_expiry = 120
    roll_days = 15
    min_volume = 0.0
    min_open_interest = 0.0

    account_value = 100000.0
    target_volatility = 0.20
    max_contract_value_fraction = 0.30
    contract_volatility = 1000.0
    point_value = 1.0
    price_add = 1.0

    parameters = [
        "fast_window",
        "slow_window",
        "adx_window",
        "adx_min",
        "exit_adx",
        "allow_short",
        "bar_window",
        "min_days_to_expiry",
        "max_days_to_expiry",
        "roll_days",
        "min_volume",
        "min_open_interest",
        "account_value",
        "target_volatility",
        "max_contract_value_fraction",
        "contract_volatility",
        "point_value",
        "price_add",
    ]
    variables = [
        "signal",
        "signal_strength",
        "adx",
        "target_pos",
        "selected_symbol",
        "days_to_expiry",
    ]

    def __init__(self, cta_engine, strategy_name: str, vt_symbol: str, setting: dict):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.signal = 0
        self.signal_strength = 0.0
        self.adx = 0.0
        self.target_pos = 0
        self.selected_symbol = ""
        self.days_to_expiry = 0
        self._model = HybridTrendModel(
            fast_window=int(self.fast_window),
            slow_window=int(self.slow_window),
            adx_window=int(self.adx_window),
            adx_min=float(self.adx_min),
            exit_adx=float(self.exit_adx),
            allow_short=bool(self.allow_short),
        )
        self._selector = ContractSelector(
            min_days_to_expiry=int(self.min_days_to_expiry),
            max_days_to_expiry=int(self.max_days_to_expiry),
            min_volume=float(self.min_volume),
            min_open_interest=float(self.min_open_interest),
        )
        self._risk = HybridRiskManager(
            target_volatility=float(self.target_volatility),
            max_contract_value_fraction=float(self.max_contract_value_fraction),
        )
        self._bar_generator = BarGenerator(
            on_bar=self.on_window_bar,
            window=max(1, int(self.bar_window)),
            on_window_bar=self.on_window_bar,
        )

    def on_init(self) -> None:
        self.write_log("HybridTrendStrategy initialized")

    def on_start(self) -> None:
        self.write_log("HybridTrendStrategy started")

    def on_stop(self) -> None:
        self.write_log("HybridTrendStrategy stopped")

    def on_tick(self, tick: TickData) -> None:
        return None

    def on_bar(self, bar: BarData) -> None:
        if int(self.bar_window) <= 1:
            self.on_window_bar(bar)
            return
        self._bar_generator.update_bar(bar)

    def on_window_bar(self, bar: BarData) -> None:
        decision = self._model.on_bar(
            HybridBar(
                datetime=bar.datetime,
                close_price=float(bar.close_price),
                high_price=float(bar.high_price),
                low_price=float(bar.low_price),
                volume=float(bar.volume),
                open_interest=float(bar.open_interest),
            ),
        )
        candidate = self._candidate_for_bar(bar, decision)
        selected = self._selector.select([candidate])
        should_roll = candidate.days_to_expiry < int(self.roll_days)
        target = self._target_position(bar, decision, selected, should_roll)

        self.signal = decision.signal
        self.signal_strength = decision.signal_strength
        self.adx = decision.adx
        self.target_pos = target
        self.selected_symbol = selected.symbol if selected else ""
        self.days_to_expiry = candidate.days_to_expiry
        self._rebalance(bar, target)
        self.put_event()

    def _candidate_for_bar(
        self,
        bar: BarData,
        decision: TrendDecision,
    ) -> ContractCandidate:
        symbol = str(getattr(bar, "symbol", "") or self.vt_symbol.split(".")[0])
        expiry = infer_contract_expiry(symbol)
        days_to_expiry = (
            (expiry - bar.datetime.date()).days
            if expiry is not None
            else int(self.max_days_to_expiry)
        )
        return ContractCandidate(
            symbol=symbol,
            expiry=expiry,
            days_to_expiry=days_to_expiry,
            volume=float(bar.volume),
            open_interest=float(bar.open_interest),
            trend_strength=decision.signal_strength,
            roll_yield=0.0,
        )

    def _target_position(
        self,
        bar: BarData,
        decision: TrendDecision,
        selected: ContractCandidate | None,
        should_roll: bool,
    ) -> int:
        if selected is None or should_roll or decision.signal == 0:
            return 0
        size = self._risk.target_size(
            portfolio_value=float(self.account_value),
            contract_volatility=float(self.contract_volatility),
            point_value=float(self.point_value),
            price=float(bar.close_price),
            signal_strength=decision.signal_strength,
        )
        return size * decision.signal

    def _rebalance(self, bar: BarData, target: int) -> None:
        current = int(self.pos)
        if target == current:
            return

        buy_price = bar.close_price + float(self.price_add)
        sell_price = bar.close_price - float(self.price_add)

        if target > current:
            volume = target - current
            if current < 0:
                closing = min(volume, abs(current))
                self.cover(buy_price, closing)
                current += closing
                volume = target - current
            if volume > 0:
                self.buy(buy_price, volume)
            return

        volume = current - target
        if current > 0:
            closing = min(volume, current)
            self.sell(sell_price, closing)
            current -= closing
            volume = current - target
        if volume > 0:
            self.short(sell_price, volume)


def infer_contract_expiry(symbol: str) -> date | None:
    """Infer a Chinese futures contract expiry month from a YYMM suffix."""
    match = EXPIRY_SUFFIX_PATTERN.search(symbol)
    if match is None:
        return None

    suffix = match.group(1)
    year = 2000 + int(suffix[:2])
    month = int(suffix[2:])
    if month < 1 or month > 12:
        return None
    return date(year, month, monthrange(year, month)[1])
