"""Credential storage adapters for authentication."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable, Protocol


ADMIN_ROLE = "admin"
USER_ROLE = "user"


@dataclass(frozen=True)
class CredentialRecord:
    email: str
    password_hash: str
    role: str


class DuplicateCredentialsError(Exception):
    """Raised when a credential record already exists for an email."""


class CredentialsStore(Protocol):
    def create_user(self, email: str, password_hash: str) -> CredentialRecord:
        """Create credentials and assign the bootstrap role atomically."""

    def find_user(self, email: str) -> CredentialRecord | None:
        """Return stored credentials for an email, if present."""


class InMemoryCredentialsStore:
    """Small credentials adapter for tests."""

    def __init__(self) -> None:
        self._records: dict[str, CredentialRecord] = {}
        self._lock = Lock()

    def create_user(self, email: str, password_hash: str) -> CredentialRecord:
        with self._lock:
            if email in self._records:
                raise DuplicateCredentialsError(email)

            role = ADMIN_ROLE if not self._records else USER_ROLE
            record = CredentialRecord(
                email=email,
                password_hash=password_hash,
                role=role,
            )
            self._records[email] = record
            return record

    def find_user(self, email: str) -> CredentialRecord | None:
        with self._lock:
            return self._records.get(email)


class PostgresCredentialsStore:
    """Postgres credentials adapter used by the production auth module."""

    def __init__(
        self,
        dsn: str,
        connect: Callable[[str], Any] | None = None,
    ) -> None:
        self._dsn = dsn
        self._connect = connect

    def create_user(self, email: str, password_hash: str) -> CredentialRecord:
        with self._connection() as connection:
            self._ensure_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute("LOCK TABLE auth_users IN SHARE ROW EXCLUSIVE MODE")
                cursor.execute("SELECT EXISTS (SELECT 1 FROM auth_users)")
                has_users = bool(cursor.fetchone()[0])
                role = USER_ROLE if has_users else ADMIN_ROLE
                try:
                    cursor.execute(
                        """
                        INSERT INTO auth_users (email, password_hash, role)
                        VALUES (%s, %s, %s)
                        RETURNING email, password_hash, role
                        """,
                        (email, password_hash, role),
                    )
                except Exception as exc:
                    if _is_unique_violation(exc):
                        raise DuplicateCredentialsError(email) from exc
                    raise
                return _record_from_row(cursor.fetchone())

    def find_user(self, email: str) -> CredentialRecord | None:
        with self._connection() as connection:
            self._ensure_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT email, password_hash, role
                    FROM auth_users
                    WHERE email = %s
                    """,
                    (email,),
                )
                row = cursor.fetchone()
                return _record_from_row(row) if row is not None else None

    def _connection(self):
        if self._connect is not None:
            return self._connect(self._dsn)

        import psycopg

        return psycopg.connect(self._dsn)

    def _ensure_schema(self, connection) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_users (
                    email TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """,
            )


def _record_from_row(row) -> CredentialRecord:
    return CredentialRecord(
        email=str(row[0]),
        password_hash=str(row[1]),
        role=str(row[2]),
    )


def _is_unique_violation(exc: Exception) -> bool:
    return getattr(exc, "sqlstate", None) == "23505"
