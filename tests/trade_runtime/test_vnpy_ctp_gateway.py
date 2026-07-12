from decimal import Decimal

from trade_runtime.adapters.vnpy_ctp.gateway import VnpyCtpOrderGateway
from trade_runtime.application.ports import BrokerSubmitOutcome
from trade_runtime.domain.orders import BrokerOrder


def _order() -> BrokerOrder:
    return BrokerOrder.create(
        broker_order_id="order-1",
        order_intent_id="intent-1",
        requested_volume=2,
        limit_price=Decimal("3258.0"),
    )


def test_vnpy_gateway_treats_a_local_order_id_as_submit_unknown():
    observed: list[BrokerOrder] = []
    gateway = VnpyCtpOrderGateway(
        send_order=lambda order: observed.append(order) or "CTP.order-1"
    )

    outcome = gateway.submit(_order())

    assert outcome is BrokerSubmitOutcome.UNKNOWN
    assert observed == [_order()]


def test_vnpy_gateway_treats_transport_exception_as_submit_unknown():
    def raise_transport_error(order: BrokerOrder) -> str:
        raise OSError("connection reset")

    outcome = VnpyCtpOrderGateway(send_order=raise_transport_error).submit(_order())

    assert outcome is BrokerSubmitOutcome.UNKNOWN


def test_vnpy_gateway_treats_missing_local_order_id_as_rejected():
    outcome = VnpyCtpOrderGateway(send_order=lambda order: "").submit(_order())

    assert outcome is BrokerSubmitOutcome.REJECTED
