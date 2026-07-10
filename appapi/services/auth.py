"""Authentication service.

The module's interface is intentionally small: callers can register, login, and
resolve a bearer token to the current user. Storage, hashing, token signing, and
role assignment stay local to this implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
import base64
import binascii
import hashlib
import hmac
import json
from pathlib import Path
import re
import secrets
import time
from typing import Any

from fastapi import HTTPException, status


ADMIN_ROLE = "admin"
USER_ROLE = "user"
HASH_ALGORITHM = "pbkdf2_sha256"
HASH_ITERATIONS = 260_000
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class AuthenticatedUser:
    email: str
    role: str


@dataclass(frozen=True)
class AuthSession:
    access_token: str
    user: AuthenticatedUser


class AuthService:
    def __init__(self, users_file: Path, token_secret: str):
        self.users_file = users_file
        self.token_secret = token_secret

    def register(self, email: str, password: str) -> AuthSession:
        normalized_email = self._normalize_email(email)
        self._validate_password(password)
        users = self._load_users()

        if self._find_user(users, normalized_email) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )

        role = ADMIN_ROLE if not users else USER_ROLE
        user_record = {
            "email": normalized_email,
            "password_hash": self._hash_password(password),
            "role": role,
        }
        users.append(user_record)
        self._save_users(users)

        user = AuthenticatedUser(email=normalized_email, role=role)
        return AuthSession(access_token=self._create_access_token(user), user=user)

    def login(self, email: str, password: str) -> AuthSession:
        normalized_email = self._normalize_email(email)
        users = self._load_users()
        user_record = self._find_user(users, normalized_email)
        if user_record is None or not self._verify_password(
            password,
            str(user_record.get("password_hash", "")),
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = AuthenticatedUser(
            email=str(user_record["email"]),
            role=str(user_record["role"]),
        )
        return AuthSession(access_token=self._create_access_token(user), user=user)

    def user_from_authorization_header(
        self,
        authorization: str | None,
    ) -> AuthenticatedUser:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        email = self._email_from_token(authorization.removeprefix("Bearer ").strip())
        users = self._load_users()
        user_record = self._find_user(users, email)
        if user_record is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return AuthenticatedUser(
            email=str(user_record["email"]),
            role=str(user_record["role"]),
        )

    def require_admin(self, user: AuthenticatedUser) -> AuthenticatedUser:
        if user.role != ADMIN_ROLE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required",
            )
        return user

    def _normalize_email(self, email: str) -> str:
        normalized_email = email.strip().lower()
        if not EMAIL_PATTERN.match(normalized_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid email address is required",
            )
        return normalized_email

    def _validate_password(self, password: str) -> None:
        if len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters",
            )

    def _create_access_token(self, user: AuthenticatedUser) -> str:
        payload = {
            "email": user.email,
            "role": user.role,
            "iat": int(time.time()),
        }
        payload_part = _base64_url_encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        )
        signature_part = self._sign(payload_part)
        return f"{payload_part}.{signature_part}"

    def _email_from_token(self, token: str) -> str:
        try:
            payload_part, signature_part = token.split(".", 1)
        except ValueError as exc:
            raise self._invalid_token_error() from exc

        expected_signature = self._sign(payload_part)
        if not hmac.compare_digest(signature_part, expected_signature):
            raise self._invalid_token_error()

        try:
            payload = json.loads(_base64_url_decode(payload_part).decode("utf-8"))
        except (ValueError, json.JSONDecodeError, binascii.Error, UnicodeDecodeError) as exc:
            raise self._invalid_token_error() from exc

        email = payload.get("email")
        if not isinstance(email, str):
            raise self._invalid_token_error()
        return self._normalize_email(email)

    def _sign(self, payload_part: str) -> str:
        digest = hmac.new(
            self.token_secret.encode("utf-8"),
            payload_part.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return _base64_url_encode(digest)

    def _load_users(self) -> list[dict[str, Any]]:
        if not self.users_file.exists():
            return []

        try:
            data = json.loads(self.users_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User store is not readable",
            ) from exc

        if not isinstance(data, list):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User store is invalid",
            )
        return [item for item in data if isinstance(item, dict)]

    def _save_users(self, users: list[dict[str, Any]]) -> None:
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.users_file.with_suffix(f"{self.users_file.suffix}.tmp")
        temp_file.write_text(
            json.dumps(users, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temp_file.replace(self.users_file)

    def _find_user(
        self,
        users: list[dict[str, Any]],
        email: str,
    ) -> dict[str, Any] | None:
        return next(
            (user for user in users if str(user.get("email", "")).lower() == email),
            None,
        )

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            HASH_ITERATIONS,
        )
        return "$".join(
            [
                HASH_ALGORITHM,
                str(HASH_ITERATIONS),
                _base64_url_encode(salt),
                _base64_url_encode(digest),
            ],
        )

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            algorithm, iterations, encoded_salt, encoded_digest = stored_hash.split(
                "$",
                3,
            )
        except ValueError:
            return False

        if algorithm != HASH_ALGORITHM:
            return False

        try:
            salt = _base64_url_decode(encoded_salt)
            expected_digest = _base64_url_decode(encoded_digest)
            iteration_count = int(iterations)
        except (ValueError, binascii.Error):
            return False

        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iteration_count,
        )
        return hmac.compare_digest(actual_digest, expected_digest)

    def _invalid_token_error(self) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _base64_url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64_url_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))
