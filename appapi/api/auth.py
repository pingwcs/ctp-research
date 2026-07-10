"""Authentication HTTP endpoints."""

from fastapi import APIRouter, Depends, Header, status

from appapi.core.config import settings
from appapi.schemas.auth import (
    AuthSessionResponse,
    AuthUserResponse,
    LoginRequest,
    RegisterRequest,
)
from appapi.services.auth import AuthService, AuthenticatedUser


router = APIRouter()
_auth_service = AuthService(
    users_file=settings.auth_users_file,
    token_secret=settings.auth_token_secret,
)


def get_auth_service() -> AuthService:
    return _auth_service


def get_current_user(
    authorization: str | None = Header(None),
    service: AuthService = Depends(get_auth_service),
) -> AuthenticatedUser:
    return service.user_from_authorization_header(authorization)


def require_admin_user(
    user: AuthenticatedUser = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> AuthenticatedUser:
    return service.require_admin(user)


@router.post(
    "/register",
    response_model=AuthSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    request: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> AuthSessionResponse:
    session = service.register(email=request.email, password=request.password)
    return _session_response(session.access_token, session.user)


@router.post("/login", response_model=AuthSessionResponse)
def login_user(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> AuthSessionResponse:
    session = service.login(email=request.email, password=request.password)
    return _session_response(session.access_token, session.user)


@router.get("/me", response_model=AuthUserResponse)
def get_me(user: AuthenticatedUser = Depends(get_current_user)) -> AuthUserResponse:
    return _user_response(user)


def _session_response(
    access_token: str,
    user: AuthenticatedUser,
) -> AuthSessionResponse:
    return AuthSessionResponse(
        access_token=access_token,
        user=_user_response(user),
    )


def _user_response(user: AuthenticatedUser) -> AuthUserResponse:
    return AuthUserResponse(email=user.email, role=user.role)
