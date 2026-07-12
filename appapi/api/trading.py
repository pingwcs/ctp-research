"""Tenant-scoped HTTP commands for manual live trading."""

from fastapi import APIRouter, Depends, Header, HTTPException, status

from appapi.api.auth import get_current_user
from appapi.core.config import settings
from appapi.schemas.trading.orders import (
    CreateOrderCommandRequest,
    OrderCommandResponse,
)
from appapi.services.auth import AuthenticatedUser
from appapi.services.trading.commands import (
    CommandConflictError,
    PostgresTradingCommandStore,
    TradingAccessDeniedError,
    TradingCommandService,
)


router = APIRouter()
_command_service = TradingCommandService(
    PostgresTradingCommandStore(settings.auth_database_dsn)
)


def get_trading_command_service() -> TradingCommandService:
    """Return the application service used by the trading HTTP boundary."""
    return _command_service


@router.post(
    "/accounts/{account_id}/orders",
    response_model=OrderCommandResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def post_create_order(
    account_id: str,
    request: CreateOrderCommandRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1),
    user: AuthenticatedUser = Depends(get_current_user),
    service: TradingCommandService = Depends(get_trading_command_service),
) -> OrderCommandResponse:
    """Persist a user intent; broker execution occurs asynchronously."""
    try:
        command = service.submit_order(
            account_id=account_id,
            actor_email=user.email,
            idempotency_key=idempotency_key,
            request=request,
        )
    except TradingAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except CommandConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return OrderCommandResponse(
        command_id=command.command_id,
        order_intent_id=command.order_intent_id,
        status="PENDING",
    )
