"""Order intent validation and broker-order state transitions."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from trade_runtime.domain.types import Direction, OffsetPolicy


class OrderIntentValidationError(ValueError):
    """Raised when a user-level order intent is structurally invalid."""


class OrderTransitionError(ValueError):
    """Raised when a broker-order status transition is not allowed."""


class BrokerOrderStatus(StrEnum):
    CREATED = "CREATED"
    RISK_CHECKING = "RISK_CHECKING"
    RISK_REJECTED = "RISK_REJECTED"
    DISPATCH_PENDING = "DISPATCH_PENDING"
    SUBMITTING = "SUBMITTING"
    SUBMIT_UNKNOWN = "SUBMIT_UNKNOWN"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCEL_UNKNOWN = "CANCEL_UNKNOWN"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    RECONCILE_REQUIRED = "RECONCILE_REQUIRED"


TERMINAL_STATUSES = frozenset(
    {
        BrokerOrderStatus.RISK_REJECTED,
        BrokerOrderStatus.FILLED,
        BrokerOrderStatus.CANCELLED,
        BrokerOrderStatus.REJECTED,
    }
)

_ALLOWED_TRANSITIONS = {
    BrokerOrderStatus.CREATED: {BrokerOrderStatus.RISK_CHECKING},
    BrokerOrderStatus.RISK_CHECKING: {
        BrokerOrderStatus.RISK_REJECTED,
        BrokerOrderStatus.DISPATCH_PENDING,
    },
    BrokerOrderStatus.DISPATCH_PENDING: {BrokerOrderStatus.SUBMITTING},
    BrokerOrderStatus.SUBMITTING: {
        BrokerOrderStatus.SUBMIT_UNKNOWN,
        BrokerOrderStatus.ACCEPTED,
        BrokerOrderStatus.REJECTED,
    },
    BrokerOrderStatus.SUBMIT_UNKNOWN: {
        BrokerOrderStatus.ACCEPTED,
        BrokerOrderStatus.REJECTED,
        BrokerOrderStatus.RECONCILE_REQUIRED,
    },
    BrokerOrderStatus.ACCEPTED: {
        BrokerOrderStatus.PARTIALLY_FILLED,
        BrokerOrderStatus.FILLED,
        BrokerOrderStatus.CANCEL_PENDING,
        BrokerOrderStatus.REJECTED,
    },
    BrokerOrderStatus.PARTIALLY_FILLED: {
        BrokerOrderStatus.FILLED,
        BrokerOrderStatus.CANCEL_PENDING,
    },
    BrokerOrderStatus.CANCEL_PENDING: {
        BrokerOrderStatus.CANCEL_UNKNOWN,
        BrokerOrderStatus.CANCELLED,
        BrokerOrderStatus.PARTIALLY_FILLED,
        BrokerOrderStatus.FILLED,
    },
    BrokerOrderStatus.CANCEL_UNKNOWN: {
        BrokerOrderStatus.CANCELLED,
        BrokerOrderStatus.PARTIALLY_FILLED,
        BrokerOrderStatus.FILLED,
        BrokerOrderStatus.RECONCILE_REQUIRED,
    },
    BrokerOrderStatus.RECONCILE_REQUIRED: {
        BrokerOrderStatus.ACCEPTED,
        BrokerOrderStatus.PARTIALLY_FILLED,
        BrokerOrderStatus.FILLED,
        BrokerOrderStatus.CANCELLED,
        BrokerOrderStatus.REJECTED,
    },
}


@dataclass(frozen=True)
class OrderIntent:
    order_intent_id: str
    account_id: str
    symbol: str
    exchange: str
    direction: Direction
    offset_policy: OffsetPolicy
    limit_price: Decimal
    volume: int

    def __post_init__(self) -> None:
        if not self.order_intent_id:
            raise OrderIntentValidationError("order_intent_id is required")
        if not self.account_id:
            raise OrderIntentValidationError("account_id is required")
        if not self.symbol:
            raise OrderIntentValidationError("symbol is required")
        if not self.exchange:
            raise OrderIntentValidationError("exchange is required")
        if self.limit_price <= Decimal("0"):
            raise OrderIntentValidationError("limit_price must be positive")
        if self.volume <= 0:
            raise OrderIntentValidationError("volume must be positive")


@dataclass(frozen=True)
class BrokerOrder:
    broker_order_id: str
    order_intent_id: str
    requested_volume: int
    limit_price: Decimal
    status: BrokerOrderStatus = BrokerOrderStatus.CREATED

    @classmethod
    def create(
        cls,
        *,
        broker_order_id: str,
        order_intent_id: str,
        requested_volume: int,
        limit_price: Decimal,
        status: BrokerOrderStatus = BrokerOrderStatus.CREATED,
    ) -> "BrokerOrder":
        return cls(
            broker_order_id=broker_order_id,
            order_intent_id=order_intent_id,
            requested_volume=requested_volume,
            limit_price=limit_price,
            status=status,
        )


def advance_broker_order(
    order: BrokerOrder,
    target_status: BrokerOrderStatus,
) -> BrokerOrder:
    """Return a new order after one valid state transition."""
    if order.status in TERMINAL_STATUSES:
        raise OrderTransitionError(f"cannot leave terminal status {order.status}")
    if target_status not in _ALLOWED_TRANSITIONS.get(order.status, set()):
        raise OrderTransitionError(
            f"invalid transition from {order.status} to {target_status}"
        )
    return BrokerOrder(
        broker_order_id=order.broker_order_id,
        order_intent_id=order.order_intent_id,
        requested_volume=order.requested_volume,
        limit_price=order.limit_price,
        status=target_status,
    )
