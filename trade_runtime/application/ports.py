"""Ports that isolate trading use cases from CTP and persistence adapters."""

from enum import StrEnum
from typing import Protocol

from trade_runtime.domain.orders import BrokerOrder


class BrokerSubmitOutcome(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class BrokerGateway(Protocol):
    """Minimal broker boundary required before a CTP adapter is introduced."""

    def submit(self, order: BrokerOrder) -> BrokerSubmitOutcome:
        """Submit one already-risk-checked broker order exactly once."""


class BrokerOrderStore(Protocol):
    """Persist every broker-order state observed by the command handler."""

    def save(self, order: BrokerOrder) -> None:
        """Record the current state as an immutable journal/projector input."""
