"""Monotonic per-account fencing leases for the single trading host."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any, Callable


@dataclass(frozen=True)
class RuntimeLease:
    account_id: str
    runtime_instance_id: str
    fencing_token: int
    expires_at: datetime


class InMemoryLeaseStore:
    """Thread-safe lease store implementing the production fencing contract."""

    def __init__(self, lease_seconds: float = 30.0) -> None:
        self._lease_seconds = lease_seconds
        self._leases: dict[str, RuntimeLease] = {}
        self._lock = Lock()

    def acquire(self, *, account_id: str, runtime_instance_id: str) -> RuntimeLease:
        with self._lock:
            current = self._leases.get(account_id)
            token = 1 if current is None else current.fencing_token + 1
            lease = RuntimeLease(
                account_id=account_id,
                runtime_instance_id=runtime_instance_id,
                fencing_token=token,
                expires_at=_expiry(self._lease_seconds),
            )
            self._leases[account_id] = lease
            return lease

    def current_token(self, account_id: str) -> int:
        with self._lock:
            return self._leases[account_id].fencing_token

    def heartbeat(
        self,
        *,
        account_id: str,
        runtime_instance_id: str,
        fencing_token: int,
    ) -> bool:
        with self._lock:
            current = self._leases.get(account_id)
            if (
                current is None
                or current.runtime_instance_id != runtime_instance_id
                or current.fencing_token != fencing_token
            ):
                return False
            self._leases[account_id] = RuntimeLease(
                account_id=account_id,
                runtime_instance_id=runtime_instance_id,
                fencing_token=fencing_token,
                expires_at=_expiry(self._lease_seconds),
            )
            return True


class PostgresLeaseStore:
    """PostgreSQL implementation that atomically advances account fencing tokens."""

    def __init__(
        self,
        dsn: str,
        connect: Callable[[str], Any] | None = None,
        lease_seconds: float = 30.0,
    ) -> None:
        self._dsn = dsn
        self._connect = connect
        self._lease_seconds = lease_seconds

    def acquire(self, *, account_id: str, runtime_instance_id: str) -> RuntimeLease:
        with self._connection() as connection:
            self._ensure_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO runtime_leases (
                        account_id, runtime_instance_id, fencing_token, expires_at
                    )
                    VALUES (%s, %s, 1, now() + (%s * interval '1 second'))
                    ON CONFLICT (account_id) DO UPDATE
                    SET runtime_instance_id = EXCLUDED.runtime_instance_id,
                        fencing_token = runtime_leases.fencing_token + 1,
                        expires_at = EXCLUDED.expires_at,
                        heartbeat_at = now()
                    RETURNING account_id, runtime_instance_id, fencing_token, expires_at
                    """,
                    (account_id, runtime_instance_id, self._lease_seconds),
                )
                return _lease_from_row(cursor.fetchone())

    def current_token(self, account_id: str) -> int:
        with self._connection() as connection:
            self._ensure_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT fencing_token FROM runtime_leases WHERE account_id = %s",
                    (account_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(account_id)
                return int(row[0])

    def heartbeat(
        self,
        *,
        account_id: str,
        runtime_instance_id: str,
        fencing_token: int,
    ) -> bool:
        with self._connection() as connection:
            self._ensure_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE runtime_leases
                    SET heartbeat_at = now(),
                        expires_at = now() + (%s * interval '1 second')
                    WHERE account_id = %s
                      AND runtime_instance_id = %s
                      AND fencing_token = %s
                    """,
                    (
                        self._lease_seconds,
                        account_id,
                        runtime_instance_id,
                        fencing_token,
                    ),
                )
                return cursor.rowcount == 1

    def _connection(self):
        if self._connect is not None:
            return self._connect(self._dsn)
        import psycopg

        return psycopg.connect(self._dsn)

    def _ensure_schema(self, connection) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_leases (
                    account_id TEXT PRIMARY KEY,
                    runtime_instance_id TEXT NOT NULL,
                    fencing_token BIGINT NOT NULL,
                    heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    expires_at TIMESTAMPTZ NOT NULL
                )
                """
            )


def _expiry(lease_seconds: float) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=lease_seconds)


def _lease_from_row(row) -> RuntimeLease:
    return RuntimeLease(
        account_id=str(row[0]),
        runtime_instance_id=str(row[1]),
        fencing_token=int(row[2]),
        expires_at=row[3],
    )
