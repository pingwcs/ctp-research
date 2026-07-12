from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trade_runtime.domain.risk import RiskInput, RiskRejectionCode, evaluate_risk
from trade_runtime.domain.types import OffsetPolicy


def test_stale_market_data_rejects_an_opening_order():
    now = datetime(2026, 7, 13, 8, 0, tzinfo=UTC)
    decision = evaluate_risk(
        RiskInput(
            offset_policy=OffsetPolicy.OPEN,
            account_ready=True,
            opening_blocked=False,
            market_timestamp=now - timedelta(seconds=6),
            market_freshness_seconds=5,
            limit_price=Decimal("3258"),
        ),
        now=now,
    )

    assert decision.allowed is False
    assert decision.code is RiskRejectionCode.STALE_MARKET_DATA


def test_closing_order_is_allowed_when_opening_is_blocked_and_market_is_stale():
    now = datetime(2026, 7, 13, 8, 0, tzinfo=UTC)
    decision = evaluate_risk(
        RiskInput(
            offset_policy=OffsetPolicy.CLOSE_AUTO,
            account_ready=True,
            opening_blocked=True,
            market_timestamp=now - timedelta(seconds=60),
            market_freshness_seconds=5,
            limit_price=Decimal("3258"),
        ),
        now=now,
    )

    assert decision.allowed is True
    assert decision.code is None
