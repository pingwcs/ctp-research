"""Tests for auth credentials storage adapters."""

import pytest

from appapi.services.auth_credentials import (
    DuplicateCredentialsError,
    PostgresCredentialsStore,
)


class FakeUniqueViolation(Exception):
    sqlstate = "23505"


class FakeCursor:
    def __init__(self, database):
        self.database = database
        self.result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params=None):
        normalized_sql = " ".join(sql.split())
        self.database.statements.append((normalized_sql, params))

        if normalized_sql.startswith("SELECT EXISTS"):
            self.result = (bool(self.database.users),)
            return

        if normalized_sql.startswith("INSERT INTO auth_users"):
            email, password_hash, role = params
            if email in self.database.users:
                raise FakeUniqueViolation()
            self.database.users[email] = {
                "email": email,
                "password_hash": password_hash,
                "role": role,
            }
            self.result = (email, password_hash, role)
            return

        if normalized_sql.startswith("SELECT email, password_hash, role"):
            user = self.database.users.get(params[0])
            self.result = (
                (user["email"], user["password_hash"], user["role"])
                if user is not None
                else None
            )
            return

        self.result = None

    def fetchone(self):
        return self.result


class FakeConnection:
    def __init__(self, database):
        self.database = database

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def cursor(self):
        return FakeCursor(self.database)


class FakeDatabase:
    def __init__(self):
        self.users = {}
        self.statements = []

    def connect(self, dsn):
        self.dsn = dsn
        return FakeConnection(self)


def test_postgres_store_creates_schema_and_assigns_first_user_admin():
    database = FakeDatabase()
    store = PostgresCredentialsStore(
        "postgresql://auth-db",
        connect=database.connect,
    )

    user = store.create_user("owner@example.com", "hashed-password")

    assert user.email == "owner@example.com"
    assert user.password_hash == "hashed-password"
    assert user.role == "admin"
    assert any(
        sql.startswith("CREATE TABLE IF NOT EXISTS auth_users")
        for sql, _params in database.statements
    )
    assert any(
        sql.startswith("INSERT INTO auth_users")
        for sql, _params in database.statements
    )


def test_postgres_store_finds_existing_user_and_rejects_duplicates():
    database = FakeDatabase()
    store = PostgresCredentialsStore(
        "postgresql://auth-db",
        connect=database.connect,
    )
    store.create_user("owner@example.com", "owner-hash")

    found = store.find_user("owner@example.com")

    assert found is not None
    assert found.email == "owner@example.com"
    with pytest.raises(DuplicateCredentialsError):
        store.create_user("owner@example.com", "other-hash")
