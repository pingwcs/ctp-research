"""Serial order command handling without a dependency on a concrete broker."""

from datetime import datetime

from trade_runtime.application.ports import (
    BrokerGateway,
    BrokerOrderStore,
    BrokerSubmitOutcome,
)
from trade_runtime.domain.orders import (
    BrokerOrder,
    BrokerOrderStatus,
    advance_broker_order,
)
from trade_runtime.domain.risk import RiskInput, evaluate_risk


class OrderCommandHandler:
    """Handle one account's submit commands in the caller's serial actor."""

    def __init__(self, *, store: BrokerOrderStore, gateway: BrokerGateway) -> None:
        self._store = store
        self._gateway = gateway

    def submit(
        self,
        order: BrokerOrder,
        *,
        risk: RiskInput,
        now: datetime,
    ) -> BrokerOrder:
        """Risk-check then submit once; an unknown result is never retried here."""
        if order.status is BrokerOrderStatus.SUBMIT_UNKNOWN:
            return order

        risk_checking = advance_broker_order(order, BrokerOrderStatus.RISK_CHECKING)
        self._store.save(risk_checking)
        decision = evaluate_risk(risk, now=now)
        if not decision.allowed:
            rejected = advance_broker_order(
                risk_checking,
                BrokerOrderStatus.RISK_REJECTED,
            )
            self._store.save(rejected)
            return rejected

        dispatch_pending = advance_broker_order(
            risk_checking,
            BrokerOrderStatus.DISPATCH_PENDING,
        )
        self._store.save(dispatch_pending)
        submitting = advance_broker_order(
            dispatch_pending,
            BrokerOrderStatus.SUBMITTING,
        )
        self._store.save(submitting)
        outcome = self._gateway.submit(submitting)
        target_status = {
            BrokerSubmitOutcome.ACCEPTED: BrokerOrderStatus.ACCEPTED,
            BrokerSubmitOutcome.REJECTED: BrokerOrderStatus.REJECTED,
            BrokerSubmitOutcome.UNKNOWN: BrokerOrderStatus.SUBMIT_UNKNOWN,
        }[outcome]
        result = advance_broker_order(submitting, target_status)
        self._store.save(result)
        return result
