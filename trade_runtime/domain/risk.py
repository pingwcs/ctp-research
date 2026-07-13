"""Fail-closed pre-trade risk decisions independent of broker adapters."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from trade_runtime.domain.types import OffsetPolicy


class RiskRejectionCode(StrEnum):
    ACCOUNT_NOT_READY = "ACCOUNT_NOT_READY"
    OPENING_BLOCKED = "OPENING_BLOCKED"
    STALE_MARKET_DATA = "STALE_MARKET_DATA"
    INVALID_LIMIT_PRICE = "INVALID_LIMIT_PRICE"


@dataclass(frozen=True)
class RiskInput:
    offset_policy: OffsetPolicy
    account_ready: bool
    opening_blocked: bool
    market_timestamp: datetime | None
    market_freshness_seconds: float
    limit_price: Decimal


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    code: RiskRejectionCode | None = None


def evaluate_risk(input: RiskInput, *, now: datetime) -> RiskDecision:
    """Apply the first fail-closed checks required before dispatching an order."""
    if not input.account_ready:
        return RiskDecision(False, RiskRejectionCode.ACCOUNT_NOT_READY)
    if input.limit_price <= Decimal("0"):
        return RiskDecision(False, RiskRejectionCode.INVALID_LIMIT_PRICE)
    if input.offset_policy is OffsetPolicy.OPEN:
        if input.opening_blocked:
            return RiskDecision(False, RiskRejectionCode.OPENING_BLOCKED)
        if input.market_timestamp is None:
            return RiskDecision(False, RiskRejectionCode.STALE_MARKET_DATA)
        age_seconds = (now - input.market_timestamp).total_seconds()
        if age_seconds > input.market_freshness_seconds:
            return RiskDecision(False, RiskRejectionCode.STALE_MARKET_DATA)
    return RiskDecision(True)
