"""Tests for appapi authentication and role behavior."""

import asyncio
import json

import pytest
from fastapi import FastAPI

from appapi.api.auth import get_auth_service, router as auth_router
from appapi.services.auth import AuthService
from appapi.services.auth_credentials import InMemoryCredentialsStore


@pytest.fixture()
def auth_client(tmp_path):
    test_app = FastAPI()
    test_app.include_router(auth_router, prefix="/api/auth")
    service = AuthService(
        credentials_store=InMemoryCredentialsStore(),
        token_secret="test-token-secret",
    )
    test_app.dependency_overrides[get_auth_service] = lambda: service
    yield ApiClient(test_app)
    test_app.dependency_overrides.clear()


class ApiResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        if not self._body:
            return None
        return json.loads(self._body.decode("utf-8"))


async def _request_async(client_app, method, path, json_body=None, headers=None):
    request_body = (
        json.dumps(json_body).encode("utf-8") if json_body is not None else b""
    )
    request_headers = [
        (b"host", b"testserver"),
        (b"content-type", b"application/json"),
    ]
    for key, value in (headers or {}).items():
        request_headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": request_headers,
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }
    sent = []
    has_sent_body = False

    async def receive():
        nonlocal has_sent_body
        if not has_sent_body:
            has_sent_body = True
            return {
                "type": "http.request",
                "body": request_body,
                "more_body": False,
            }
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    await client_app(scope, receive, send)

    status_code = next(
        message["status"]
        for message in sent
        if message["type"] == "http.response.start"
    )
    body = b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    )
    return ApiResponse(status_code, body)


class ApiClient:
    def __init__(self, client_app):
        self._app = client_app

    def get(self, path, headers=None):
        return asyncio.run(_request_async(self._app, "GET", path, headers=headers))

    def post(self, path, json=None, headers=None):
        return asyncio.run(
            _request_async(self._app, "POST", path, json_body=json, headers=headers),
        )


def _register(client: ApiClient, email: str, password: str = "correct-horse"):
    return client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )


def test_registers_first_email_user_as_admin_and_token_reads_me(auth_client):
    response = _register(auth_client, "OWNER@Example.COM")

    assert response.status_code == 201
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["user"] == {
        "email": "owner@example.com",
        "role": "admin",
    }

    me_response = auth_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json() == {"email": "owner@example.com", "role": "admin"}


def test_registers_later_email_users_as_ordinary_users(auth_client):
    _register(auth_client, "owner@example.com")

    response = _register(auth_client, "member@example.com")

    assert response.status_code == 201
    assert response.json()["user"] == {
        "email": "member@example.com",
        "role": "user",
    }


def test_registration_rejects_duplicate_email_case_insensitively(auth_client):
    _register(auth_client, "owner@example.com")

    response = _register(auth_client, "OWNER@example.com")

    assert response.status_code == 409
    assert response.json()["detail"] == "Email is already registered"


def test_login_uses_email_credentials_and_rejects_bad_password(auth_client):
    _register(auth_client, "owner@example.com", password="correct-horse")

    response = auth_client.post(
        "/api/auth/login",
        json={"email": "OWNER@example.com", "password": "correct-horse"},
    )
    bad_password_response = auth_client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 200
    assert response.json()["user"] == {"email": "owner@example.com", "role": "admin"}
    assert bad_password_response.status_code == 401
    assert bad_password_response.json()["detail"] == "Invalid email or password"


def test_me_requires_a_valid_bearer_token(auth_client):
    missing_response = auth_client.get("/api/auth/me")
    malformed_response = auth_client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not-a-token"},
    )

    assert missing_response.status_code == 401
    assert malformed_response.status_code == 401


def test_register_accepts_email_and_password_only(auth_client):
    response = auth_client.post(
        "/api/auth/register",
        json={
            "email": "owner@example.com",
            "password": "correct-horse",
            "username": "owner",
        },
    )

    assert response.status_code == 422
