from decimal import Decimal

import pytest

from trade_runtime.domain.orders import (
    BrokerOrder,
    BrokerOrderStatus,
    OrderIntent,
    OrderIntentValidationError,
    OrderTransitionError,
    advance_broker_order,
)
from trade_runtime.domain.types import Direction, OffsetPolicy


def test_broker_order_accepts_a_valid_submit_to_accepted_transition():
    order = BrokerOrder.create(
        broker_order_id="order-1",
        order_intent_id="intent-1",
        requested_volume=2,
        limit_price=Decimal("3258.0"),
    )

    risk_checking = advance_broker_order(order, BrokerOrderStatus.RISK_CHECKING)
    dispatch_pending = advance_broker_order(
        risk_checking,
        BrokerOrderStatus.DISPATCH_PENDING,
    )
    submitting = advance_broker_order(
        dispatch_pending,
        BrokerOrderStatus.SUBMITTING,
    )
    accepted = advance_broker_order(submitting, BrokerOrderStatus.ACCEPTED)

    assert accepted.status is BrokerOrderStatus.ACCEPTED
    assert accepted.requested_volume == 2


def test_broker_order_rejects_transition_out_of_a_terminal_state():
    filled = BrokerOrder.create(
        broker_order_id="order-1",
        order_intent_id="intent-1",
        requested_volume=1,
        limit_price=Decimal("3258.0"),
        status=BrokerOrderStatus.FILLED,
    )

    with pytest.raises(OrderTransitionError, match="terminal"):
        advance_broker_order(filled, BrokerOrderStatus.CANCELLED)


def test_close_auto_limit_order_intent_is_valid():
    intent = OrderIntent(
        order_intent_id="intent-1",
        account_id="account-1",
        symbol="rb2610",
        exchange="SHFE",
        direction=Direction.SHORT,
        offset_policy=OffsetPolicy.CLOSE_AUTO,
        limit_price=Decimal("3258.0"),
        volume=2,
    )

    assert intent.offset_policy is OffsetPolicy.CLOSE_AUTO


def test_order_intent_rejects_non_positive_limit_price():
    with pytest.raises(OrderIntentValidationError, match="limit_price"):
        OrderIntent(
            order_intent_id="intent-1",
            account_id="account-1",
            symbol="rb2610",
            exchange="SHFE",
            direction=Direction.LONG,
            offset_policy=OffsetPolicy.OPEN,
            limit_price=Decimal("0"),
            volume=1,
        )
