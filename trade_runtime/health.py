"""Container health contract for an account-isolated trading runtime."""

from dataclasses import dataclass
from typing import Literal


RuntimeHealthStatus = Literal["READY", "DEGRADED", "UNHEALTHY"]


@dataclass(frozen=True)
class RuntimeHealthSnapshot:
    """Separate process, CTP-session, and reconciliation readiness signals."""

    process_alive: bool
    ctp_connected: bool
    account_ready: bool

    @property
    def status(self) -> RuntimeHealthStatus:
        if not self.process_alive:
            return "UNHEALTHY"
        if self.ctp_connected and self.account_ready:
            return "READY"
        return "DEGRADED"
