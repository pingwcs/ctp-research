from decimal import Decimal

import pytest

from appapi.schemas.trading.orders import CreateOrderCommandRequest
from appapi.services.trading.commands import (
    CommandConflictError,
    InMemoryTradingCommandStore,
    TradingAccessDeniedError,
    TradingCommandService,
)


def _request(volume: int = 2) -> CreateOrderCommandRequest:
    return CreateOrderCommandRequest(
        symbol="rb2610",
        exchange="SHFE",
        direction="LONG",
        offset_policy="OPEN",
        limit_price=Decimal("3258.0"),
        volume=volume,
    )


def _service() -> TradingCommandService:
    store = InMemoryTradingCommandStore()
    store.add_account(
        account_id="account-1",
        tenant_id="tenant-1",
        members={"trader@example.com"},
    )
    return TradingCommandService(store)


def test_submit_order_returns_the_original_command_for_same_idempotency_key():
    service = _service()

    first = service.submit_order(
        account_id="account-1",
        actor_email="trader@example.com",
        idempotency_key="key-1",
        request=_request(),
    )
    repeated = service.submit_order(
        account_id="account-1",
        actor_email="trader@example.com",
        idempotency_key="key-1",
        request=_request(),
    )

    assert repeated.command_id == first.command_id
    assert repeated.order_intent_id == first.order_intent_id
    assert repeated.status == "PENDING"


def test_submit_order_rejects_idempotency_key_reuse_with_different_payload():
    service = _service()
    service.submit_order(
        account_id="account-1",
        actor_email="trader@example.com",
        idempotency_key="key-1",
        request=_request(),
    )

    with pytest.raises(CommandConflictError, match="different payload"):
        service.submit_order(
            account_id="account-1",
            actor_email="trader@example.com",
            idempotency_key="key-1",
            request=_request(volume=3),
        )


def test_submit_order_rejects_user_outside_account_tenant():
    with pytest.raises(TradingAccessDeniedError, match="not a member"):
        _service().submit_order(
            account_id="account-1",
            actor_email="other@example.com",
            idempotency_key="key-1",
            request=_request(),
        )
