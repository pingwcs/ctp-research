"""Safe submit-result mapping for a future vn.py CTP gateway adapter."""

from collections.abc import Callable

from trade_runtime.application.ports import BrokerSubmitOutcome
from trade_runtime.domain.orders import BrokerOrder


class VnpyCtpOrderGateway:
    """Map a local vn.py order-id response without claiming broker acceptance.

    `send_order` will later wrap `MainEngine.send_order`. A non-empty local
    order id proves only that vn.py accepted the request locally; the order
    stays `SUBMIT_UNKNOWN` until a CTP callback or broker query confirms it.
    """

    def __init__(self, send_order: Callable[[BrokerOrder], str | None]) -> None:
        self._send_order = send_order

    def submit(self, order: BrokerOrder) -> BrokerSubmitOutcome:
        try:
            local_order_id = self._send_order(order)
        except OSError:
            return BrokerSubmitOutcome.UNKNOWN
        if local_order_id:
            return BrokerSubmitOutcome.UNKNOWN
        return BrokerSubmitOutcome.REJECTED
