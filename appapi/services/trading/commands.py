"""Durably-shaped tenant-scoped command creation for manual orders."""

from __future__ import annotations

from dataclasses import dataclass
import json
from threading import Lock
from typing import Any, Callable, Protocol
from uuid import uuid4

from appapi.schemas.trading.orders import CreateOrderCommandRequest
from trade_runtime.domain.idempotency import payload_hash


class TradingAccessDeniedError(PermissionError):
    """Raised when a user is not a member of the account's tenant."""


class CommandConflictError(ValueError):
    """Raised when a key is reused for a different command payload."""


@dataclass(frozen=True)
class TradingCommand:
    command_id: str
    order_intent_id: str
    tenant_id: str
    account_id: str
    actor_email: str
    idempotency_key: str
    payload_hash: str
    payload: dict[str, Any]
    status: str = "PENDING"


class TradingCommandStore(Protocol):
    """Persistence port for account authorization and command creation."""

    def tenant_for_member(self, account_id: str, actor_email: str) -> str | None:
        """Return the authorized tenant for an account/user pair."""

    def find_command(
        self,
        tenant_id: str,
        account_id: str,
        idempotency_key: str,
    ) -> TradingCommand | None:
        """Look up an existing command by its tenant-scoped idempotency key."""

    def insert_command(self, command: TradingCommand) -> None:
        """Insert a newly created pending command in the store transaction."""


class InMemoryTradingCommandStore:
    """Thread-safe development/test adapter with the production uniqueness rules."""

    def __init__(self) -> None:
        self._accounts: dict[str, tuple[str, set[str]]] = {}
        self._commands: dict[tuple[str, str, str], TradingCommand] = {}
        self._lock = Lock()

    def add_account(
        self,
        *,
        account_id: str,
        tenant_id: str,
        members: set[str],
    ) -> None:
        with self._lock:
            self._accounts[account_id] = (tenant_id, set(members))

    def tenant_for_member(self, account_id: str, actor_email: str) -> str | None:
        with self._lock:
            account = self._accounts.get(account_id)
            if account is None:
                return None
            tenant_id, members = account
            return tenant_id if actor_email in members else None

    def find_command(
        self,
        tenant_id: str,
        account_id: str,
        idempotency_key: str,
    ) -> TradingCommand | None:
        with self._lock:
            return self._commands.get((tenant_id, account_id, idempotency_key))

    def insert_command(self, command: TradingCommand) -> None:
        key = (command.tenant_id, command.account_id, command.idempotency_key)
        with self._lock:
            if key in self._commands:
                raise CommandConflictError("idempotency key already exists")
            self._commands[key] = command


class PostgresTradingCommandStore:
    """PostgreSQL command store with an atomic command/order/outbox transaction."""

    def __init__(
        self,
        dsn: str,
        connect: Callable[[str], Any] | None = None,
    ) -> None:
        self._dsn = dsn
        self._connect = connect

    def tenant_for_member(self, account_id: str, actor_email: str) -> str | None:
        with self._connection() as connection:
            self._ensure_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT account.tenant_id
                    FROM trading_accounts AS account
                    JOIN tenant_members AS member
                      ON member.tenant_id = account.tenant_id
                    WHERE account.id = %s AND member.user_email = %s
                    """,
                    (account_id, actor_email),
                )
                row = cursor.fetchone()
                return str(row[0]) if row else None

    def find_command(
        self,
        tenant_id: str,
        account_id: str,
        idempotency_key: str,
    ) -> TradingCommand | None:
        with self._connection() as connection:
            self._ensure_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT command_id, order_intent_id, tenant_id, account_id,
                           actor_email, idempotency_key, payload_hash,
                           payload_json, status
                    FROM trade_commands
                    WHERE tenant_id = %s
                      AND account_id = %s
                      AND idempotency_key = %s
                    """,
                    (tenant_id, account_id, idempotency_key),
                )
                row = cursor.fetchone()
                return _command_from_row(row) if row else None

    def insert_command(self, command: TradingCommand) -> None:
        with self._connection() as connection:
            self._ensure_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO trade_commands (
                        command_id, order_intent_id, tenant_id, account_id,
                        actor_email, idempotency_key, payload_hash,
                        payload_json, status
                    )
                    SELECT %s, %s, account.tenant_id, account.id,
                           %s, %s, %s, %s::jsonb, 'PENDING'
                    FROM trading_accounts AS account
                    JOIN tenant_members AS member
                      ON member.tenant_id = account.tenant_id
                    WHERE account.id = %s AND member.user_email = %s
                    """,
                    (
                        command.command_id,
                        command.order_intent_id,
                        command.actor_email,
                        command.idempotency_key,
                        command.payload_hash,
                        json.dumps(command.payload, separators=(",", ":")),
                        command.account_id,
                        command.actor_email,
                    ),
                )
                if cursor.rowcount != 1:
                    raise TradingAccessDeniedError(
                        "user is not a member of this account tenant"
                    )
                cursor.execute(
                    """
                    INSERT INTO order_intents (
                        order_intent_id, tenant_id, account_id, actor_email,
                        symbol, exchange, direction, offset_policy,
                        limit_price, volume, status
                    )
                    SELECT %s, tenant_id, account_id, actor_email,
                           %s, %s, %s, %s, %s, %s, 'CREATED'
                    FROM trade_commands
                    WHERE command_id = %s
                    """,
                    (
                        command.order_intent_id,
                        command.payload["symbol"],
                        command.payload["exchange"],
                        command.payload["direction"],
                        command.payload["offset_policy"],
                        command.payload["limit_price"],
                        command.payload["volume"],
                        command.command_id,
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO trade_outbox (message_id, account_id, message_type, payload_json)
                    VALUES (%s, %s, 'ORDER_SUBMIT_REQUESTED', %s::jsonb)
                    """,
                    (
                        str(uuid4()),
                        command.account_id,
                        json.dumps(
                            {
                                "command_id": command.command_id,
                                "order_intent_id": command.order_intent_id,
                            },
                            separators=(",", ":"),
                        ),
                    ),
                )

    def _connection(self):
        if self._connect is not None:
            return self._connect(self._dsn)
        import psycopg

        return psycopg.connect(self._dsn)

    def _ensure_schema(self, connection) -> None:
        with connection.cursor() as cursor:
            cursor.execute(TRADING_SCHEMA_SQL)


class TradingCommandService:
    """Create one durable command per authorized manual-order request."""

    def __init__(self, store: TradingCommandStore) -> None:
        self._store = store

    def submit_order(
        self,
        *,
        account_id: str,
        actor_email: str,
        idempotency_key: str,
        request: CreateOrderCommandRequest,
    ) -> TradingCommand:
        if not idempotency_key.strip():
            raise ValueError("idempotency key is required")
        tenant_id = self._store.tenant_for_member(account_id, actor_email)
        if tenant_id is None:
            raise TradingAccessDeniedError("user is not a member of this account tenant")

        request_hash = payload_hash(request.model_dump(mode="json"))
        existing = self._store.find_command(tenant_id, account_id, idempotency_key)
        if existing is not None:
            if existing.payload_hash != request_hash:
                raise CommandConflictError(
                    "idempotency key was already used with a different payload"
                )
            return existing

        command = TradingCommand(
            command_id=str(uuid4()),
            order_intent_id=str(uuid4()),
            tenant_id=tenant_id,
            account_id=account_id,
            actor_email=actor_email,
            idempotency_key=idempotency_key,
            payload_hash=request_hash,
            payload=request.model_dump(mode="json"),
        )
        self._store.insert_command(command)
        return command


def _command_from_row(row) -> TradingCommand:
    payload = row[7]
    if isinstance(payload, str):
        payload = json.loads(payload)
    return TradingCommand(
        command_id=str(row[0]),
        order_intent_id=str(row[1]),
        tenant_id=str(row[2]),
        account_id=str(row[3]),
        actor_email=str(row[4]),
        idempotency_key=str(row[5]),
        payload_hash=str(row[6]),
        payload=dict(payload),
        status=str(row[8]),
    )


TRADING_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS tenant_members (
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    user_email TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'trader', 'viewer')),
    PRIMARY KEY (tenant_id, user_email)
);
CREATE TABLE IF NOT EXISTS trading_accounts (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    broker_id TEXT NOT NULL,
    ctp_user_id TEXT NOT NULL,
    environment TEXT NOT NULL CHECK (environment IN ('SIMNOW', 'LIVE')),
    desired_state TEXT NOT NULL DEFAULT 'STOPPED',
    runtime_state TEXT NOT NULL DEFAULT 'STOPPED',
    runtime_image_digest TEXT NOT NULL,
    settlement_auto_confirm_authorized BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, broker_id, ctp_user_id, environment)
);
CREATE TABLE IF NOT EXISTS trade_commands (
    command_id TEXT PRIMARY KEY,
    order_intent_id TEXT NOT NULL UNIQUE,
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    account_id TEXT NOT NULL REFERENCES trading_accounts(id),
    actor_email TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, account_id, idempotency_key)
);
CREATE TABLE IF NOT EXISTS order_intents (
    order_intent_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    account_id TEXT NOT NULL REFERENCES trading_accounts(id),
    actor_email TEXT NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    direction TEXT NOT NULL,
    offset_policy TEXT NOT NULL,
    limit_price NUMERIC(20, 8) NOT NULL,
    volume INTEGER NOT NULL CHECK (volume > 0),
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS broker_orders (
    broker_order_id TEXT PRIMARY KEY,
    order_intent_id TEXT NOT NULL REFERENCES order_intents(order_intent_id),
    child_index INTEGER NOT NULL,
    offset TEXT NOT NULL,
    requested_volume INTEGER NOT NULL CHECK (requested_volume > 0),
    traded_volume INTEGER NOT NULL DEFAULT 0 CHECK (traded_volume >= 0),
    limit_price NUMERIC(20, 8) NOT NULL,
    status TEXT NOT NULL,
    order_ref TEXT,
    front_id INTEGER,
    session_id INTEGER,
    exchange_id TEXT,
    order_sys_id TEXT,
    UNIQUE (order_intent_id, child_index)
);
CREATE TABLE IF NOT EXISTS trade_event_journal (
    event_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES trading_accounts(id),
    runtime_instance_id TEXT NOT NULL,
    fencing_token BIGINT NOT NULL,
    trading_day TEXT NOT NULL,
    source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source_sequence TEXT,
    payload_json JSONB NOT NULL,
    payload_schema_version INTEGER NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (account_id, source, source_sequence)
);
CREATE TABLE IF NOT EXISTS trade_outbox (
    message_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES trading_accounts(id),
    message_type TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    dispatched_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS runtime_inbox (
    runtime_instance_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (runtime_instance_id, message_id)
);
"""
