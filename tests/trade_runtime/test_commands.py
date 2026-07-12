from datetime import UTC, datetime
from decimal import Decimal

from trade_runtime.application.commands import OrderCommandHandler
from trade_runtime.application.ports import BrokerSubmitOutcome
from trade_runtime.domain.orders import BrokerOrder, BrokerOrderStatus
from trade_runtime.domain.risk import RiskInput
from trade_runtime.domain.types import OffsetPolicy


class RecordingStore:
    def __init__(self) -> None:
        self.saved: list[BrokerOrder] = []

    def save(self, order: BrokerOrder) -> None:
        self.saved.append(order)


class FakeGateway:
    def __init__(self, outcome: BrokerSubmitOutcome) -> None:
        self.outcome = outcome
        self.submit_calls = 0

    def submit(self, order: BrokerOrder) -> BrokerSubmitOutcome:
        self.submit_calls += 1
        return self.outcome


def _order() -> BrokerOrder:
    return BrokerOrder.create(
        broker_order_id="order-1",
        order_intent_id="intent-1",
        requested_volume=2,
        limit_price=Decimal("3258"),
    )


def _opening_risk() -> RiskInput:
    return RiskInput(
        offset_policy=OffsetPolicy.OPEN,
        account_ready=True,
        opening_blocked=False,
        market_timestamp=datetime(2026, 7, 13, 8, 0, tzinfo=UTC),
        market_freshness_seconds=5,
        limit_price=Decimal("3258"),
    )


def test_handler_rejects_risk_before_calling_the_broker_gateway():
    store = RecordingStore()
    gateway = FakeGateway(BrokerSubmitOutcome.ACCEPTED)
    handler = OrderCommandHandler(store=store, gateway=gateway)
    risk = RiskInput(
        offset_policy=OffsetPolicy.OPEN,
        account_ready=False,
        opening_blocked=False,
        market_timestamp=None,
        market_freshness_seconds=5,
        limit_price=Decimal("3258"),
    )

    result = handler.submit(_order(), risk=risk, now=datetime(2026, 7, 13, tzinfo=UTC))

    assert result.status is BrokerOrderStatus.RISK_REJECTED
    assert gateway.submit_calls == 0
    assert store.saved[-1].status is BrokerOrderStatus.RISK_REJECTED


def test_handler_records_accepted_order_after_one_gateway_submit():
    store = RecordingStore()
    gateway = FakeGateway(BrokerSubmitOutcome.ACCEPTED)
    handler = OrderCommandHandler(store=store, gateway=gateway)

    result = handler.submit(
        _order(),
        risk=_opening_risk(),
        now=datetime(2026, 7, 13, 8, 0, tzinfo=UTC),
    )

    assert result.status is BrokerOrderStatus.ACCEPTED
    assert gateway.submit_calls == 1
    assert [item.status for item in store.saved] == [
        BrokerOrderStatus.RISK_CHECKING,
        BrokerOrderStatus.DISPATCH_PENDING,
        BrokerOrderStatus.SUBMITTING,
        BrokerOrderStatus.ACCEPTED,
    ]


def test_handler_never_resubmits_an_order_with_unknown_submit_result():
    store = RecordingStore()
    gateway = FakeGateway(BrokerSubmitOutcome.UNKNOWN)
    handler = OrderCommandHandler(store=store, gateway=gateway)

    unknown = handler.submit(
        _order(),
        risk=_opening_risk(),
        now=datetime(2026, 7, 13, 8, 0, tzinfo=UTC),
    )
    repeated = handler.submit(
        unknown,
        risk=_opening_risk(),
        now=datetime(2026, 7, 13, 8, 0, tzinfo=UTC),
    )

    assert unknown.status is BrokerOrderStatus.SUBMIT_UNKNOWN
    assert repeated is unknown
    assert gateway.submit_calls == 1
