"""Authentication request and response schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


UserRole = Literal["admin", "user"]


class AuthCredentials(BaseModel):
    """Email credentials accepted by register and login endpoints."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=8, max_length=256)


class RegisterRequest(AuthCredentials):
    """Email-only registration request."""


class LoginRequest(AuthCredentials):
    """Email login request."""


class AuthUserResponse(BaseModel):
    """Authenticated user identity returned to the frontend."""

    email: str
    role: UserRole


class AuthSessionResponse(BaseModel):
    """Bearer token plus user identity returned after register/login."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: AuthUserResponse
