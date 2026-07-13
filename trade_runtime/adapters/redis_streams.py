"""Redis Streams transport helpers and runtime-side fencing/de-duplication."""

from __future__ import annotations

from dataclasses import dataclass
import json
from threading import Lock
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class RuntimeCommandEnvelope:
    message_id: str
    account_id: str
    fencing_token: int
    payload: dict[str, Any]


class RuntimeInbox(Protocol):
    """Exactly-once effect guard on top of at-least-once stream delivery."""

    def claim(self, runtime_instance_id: str, message_id: str) -> bool:
        """Return true once for a runtime/message pair, then false forever."""


class FencingTokenAuthority(Protocol):
    """Provides the supervisor-owned current fencing token for an account."""

    def current_token(self, account_id: str) -> int:
        """Return the only token allowed to perform account side effects."""


class RedisStreamsClient(Protocol):
    """Small synchronous subset of redis-py's stream client."""

    def xadd(self, name: str, fields: dict[str, str]) -> str:
        """Append one field map to a stream and return its stream entry id."""


class InMemoryRuntimeInbox:
    """Thread-safe inbox for unit tests and a local non-durable development runtime."""

    def __init__(self) -> None:
        self._claimed: set[tuple[str, str]] = set()
        self._lock = Lock()

    def claim(self, runtime_instance_id: str, message_id: str) -> bool:
        key = (runtime_instance_id, message_id)
        with self._lock:
            if key in self._claimed:
                return False
            self._claimed.add(key)
            return True


class RedisCommandPublisher:
    """Publish account-partitioned commands without making Redis authoritative."""

    def __init__(self, client: RedisStreamsClient) -> None:
        self._client = client

    def publish(self, envelope: RuntimeCommandEnvelope) -> str:
        return self._client.xadd(
            f"trade:commands:{envelope.account_id}",
            {
                "message_id": envelope.message_id,
                "account_id": envelope.account_id,
                "fencing_token": str(envelope.fencing_token),
                "payload": json.dumps(
                    envelope.payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            },
        )


class FencedCommandConsumer:
    """Reject obsolete runtimes and run one handler effect per inbox message."""

    def __init__(
        self,
        *,
        inbox: RuntimeInbox,
        token_authority: FencingTokenAuthority,
        handle: Callable[[RuntimeCommandEnvelope], None],
        runtime_instance_id: str = "runtime-local",
    ) -> None:
        self._inbox = inbox
        self._token_authority = token_authority
        self._handle = handle
        self._runtime_instance_id = runtime_instance_id

    def consume(self, envelope: RuntimeCommandEnvelope) -> bool:
        """Run the command only if the message token is current and new."""
        if envelope.fencing_token != self._token_authority.current_token(
            envelope.account_id
        ):
            return False
        if not self._inbox.claim(self._runtime_instance_id, envelope.message_id):
            return False
        self._handle(envelope)
        return True
