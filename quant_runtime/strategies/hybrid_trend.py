"""Hybrid trend following strategy primitives.

This module keeps signal generation, contract selection, and risk sizing behind
one small interface so vn.py adapters and tests exercise the same rules.
"""

from collections import deque
from dataclasses import dataclass
from datetime import date, datetime
from math import floor


@dataclass(frozen=True)
class HybridBar:
    """Market bar fields needed by the hybrid trend module."""

    datetime: datetime
    close_price: float
    high_price: float
    low_price: float
    volume: float
    open_interest: float


@dataclass(frozen=True)
class TrendDecision:
    """Signal layer output consumed by execution and risk logic."""

    signal: int
    signal_strength: float
    adx: float
    reason: str


@dataclass(frozen=True)
class ContractCandidate:
    """Execution layer contract candidate for dynamic selection."""

    symbol: str
    expiry: date | None
    days_to_expiry: int
    volume: float
    open_interest: float
    trend_strength: float
    roll_yield: float = 0.0


class HybridTrendModel:
    """Signal layer for clean trend signals from a continuous price stream."""

    def __init__(
        self,
        fast_window: int = 50,
        slow_window: int = 200,
        adx_window: int = 14,
        adx_min: float = 25.0,
        exit_adx: float = 20.0,
        allow_short: bool = True,
    ) -> None:
        if fast_window <= 0 or slow_window <= 0 or adx_window <= 0:
            raise ValueError("windows must be positive")
        if fast_window >= slow_window:
            raise ValueError("fast_window must be smaller than slow_window")

        self.fast_window = fast_window
        self.slow_window = slow_window
        self.adx_window = adx_window
        self.adx_min = adx_min
        self.exit_adx = exit_adx
        self.allow_short = allow_short

        max_window = max(slow_window, adx_window + 1)
        self._closes: deque[float] = deque(maxlen=max_window)
        self._highs: deque[float] = deque(maxlen=adx_window + 1)
        self._lows: deque[float] = deque(maxlen=adx_window + 1)
        self._true_ranges: deque[float] = deque(maxlen=adx_window)
        self._plus_dm: deque[float] = deque(maxlen=adx_window)
        self._minus_dm: deque[float] = deque(maxlen=adx_window)
        self._dx_values: deque[float] = deque(maxlen=adx_window)
        self._last_signal = 0

    def on_bar(self, bar: HybridBar) -> TrendDecision:
        """Update the signal model and return the latest trend decision."""
        self._update_adx_inputs(bar)
        self._closes.append(float(bar.close_price))

        if len(self._closes) < self.slow_window:
            return TrendDecision(0, 0.0, self._adx(), "warming_up")

        values = list(self._closes)
        fast_ma = _mean(values[-self.fast_window :])
        slow_ma = _mean(values[-self.slow_window :])
        adx = self._adx()
        distance = abs(fast_ma - slow_ma) / slow_ma if slow_ma else 0.0
        strength = min(1.0, max(0.0, distance * 10.0 + adx / 100.0))

        long_signal = fast_ma > slow_ma and bar.close_price > slow_ma
        short_signal = fast_ma < slow_ma and bar.close_price < slow_ma
        if long_signal and adx >= self.adx_min:
            self._last_signal = 1
            return TrendDecision(1, strength, adx, "trend_long")
        if self.allow_short and short_signal and adx >= self.adx_min:
            self._last_signal = -1
            return TrendDecision(-1, strength, adx, "trend_short")
        if self._last_signal and adx < self.exit_adx:
            self._last_signal = 0
            return TrendDecision(0, 0.0, adx, "trend_weak")

        self._last_signal = 0
        return TrendDecision(0, 0.0, adx, "flat")

    def _update_adx_inputs(self, bar: HybridBar) -> None:
        if self._highs:
            previous_high = self._highs[-1]
            previous_low = self._lows[-1]
            previous_close = self._closes[-1] if self._closes else bar.close_price

            up_move = float(bar.high_price) - previous_high
            down_move = previous_low - float(bar.low_price)
            plus_dm = up_move if up_move > down_move and up_move > 0 else 0.0
            minus_dm = down_move if down_move > up_move and down_move > 0 else 0.0
            true_range = max(
                float(bar.high_price) - float(bar.low_price),
                abs(float(bar.high_price) - previous_close),
                abs(float(bar.low_price) - previous_close),
            )
            self._plus_dm.append(plus_dm)
            self._minus_dm.append(minus_dm)
            self._true_ranges.append(true_range)

            dx = self._dx()
            if dx is not None:
                self._dx_values.append(dx)

        self._highs.append(float(bar.high_price))
        self._lows.append(float(bar.low_price))

    def _dx(self) -> float | None:
        true_range = sum(self._true_ranges)
        if true_range <= 0:
            return None

        plus_di = 100.0 * sum(self._plus_dm) / true_range
        minus_di = 100.0 * sum(self._minus_dm) / true_range
        denominator = plus_di + minus_di
        if denominator <= 0:
            return None
        return 100.0 * abs(plus_di - minus_di) / denominator

    def _adx(self) -> float:
        if not self._dx_values:
            return 0.0
        return _mean(list(self._dx_values))


class ContractSelector:
    """Execution layer contract selector with liquidity and roll scoring."""

    def __init__(
        self,
        min_days_to_expiry: int = 30,
        max_days_to_expiry: int = 120,
        min_volume: float = 0.0,
        min_open_interest: float = 0.0,
    ) -> None:
        self.min_days_to_expiry = min_days_to_expiry
        self.max_days_to_expiry = max_days_to_expiry
        self.min_volume = min_volume
        self.min_open_interest = min_open_interest

    def select(
        self,
        candidates: list[ContractCandidate],
    ) -> ContractCandidate | None:
        """Return the highest-scoring valid contract candidate."""
        valid = [item for item in candidates if self._is_valid(item)]
        if not valid:
            return None

        max_volume = max(item.volume for item in valid) or 1.0
        max_open_interest = max(item.open_interest for item in valid) or 1.0
        max_roll = max((max(0.0, item.roll_yield) for item in valid), default=0.0)
        roll_denominator = max_roll or 1.0

        return max(
            valid,
            key=lambda item: (
                0.30 * (item.volume / max_volume)
                + 0.20 * (item.open_interest / max_open_interest)
                + 0.35 * max(0.0, item.trend_strength)
                + 0.15 * (max(0.0, item.roll_yield) / roll_denominator),
                -item.days_to_expiry,
                item.symbol,
            ),
        )

    def _is_valid(self, candidate: ContractCandidate) -> bool:
        return (
            self.min_days_to_expiry
            <= candidate.days_to_expiry
            <= self.max_days_to_expiry
            and candidate.volume >= self.min_volume
            and candidate.open_interest >= self.min_open_interest
        )


class HybridRiskManager:
    """Risk layer for volatility-targeted contract sizing."""

    def __init__(
        self,
        target_volatility: float = 0.20,
        max_contract_value_fraction: float = 0.30,
        drawdown_cut_fraction: float = 0.50,
        drawdown_cut_threshold: float = 0.15,
    ) -> None:
        self.target_volatility = target_volatility
        self.max_contract_value_fraction = max_contract_value_fraction
        self.drawdown_cut_fraction = drawdown_cut_fraction
        self.drawdown_cut_threshold = drawdown_cut_threshold

    def target_size(
        self,
        portfolio_value: float,
        contract_volatility: float,
        point_value: float,
        price: float,
        signal_strength: float,
        drawdown_fraction: float = 0.0,
    ) -> int:
        """Return target absolute contract count for a signal."""
        if (
            portfolio_value <= 0
            or contract_volatility <= 0
            or point_value <= 0
            or price <= 0
            or signal_strength <= 0
        ):
            return 0

        exposure_multiplier = (
            self.drawdown_cut_fraction
            if drawdown_fraction >= self.drawdown_cut_threshold
            else 1.0
        )
        raw_size = (
            self.target_volatility
            * portfolio_value
            * min(1.0, signal_strength)
            * exposure_multiplier
            / (contract_volatility * point_value)
        )
        max_size = (
            portfolio_value
            * self.max_contract_value_fraction
            / (price * point_value)
        )
        return max(0, floor(min(raw_size, max_size)))


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0

