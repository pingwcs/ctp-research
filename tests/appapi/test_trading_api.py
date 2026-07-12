from decimal import Decimal

from appapi.api.trading import post_create_order
from appapi.schemas.trading.orders import CreateOrderCommandRequest
from appapi.services.auth import AuthenticatedUser
from appapi.services.trading.commands import (
    InMemoryTradingCommandStore,
    TradingCommandService,
)


def test_post_order_creates_tenant_scoped_pending_command():
    store = InMemoryTradingCommandStore()
    store.add_account(
        account_id="account-1",
        tenant_id="tenant-1",
        members={"trader@example.com"},
    )
    response = post_create_order(
        account_id="account-1",
        idempotency_key="request-1",
        request=CreateOrderCommandRequest(
            symbol="rb2610",
            exchange="SHFE",
            direction="LONG",
            offset_policy="OPEN",
            limit_price=Decimal("3258.0"),
            volume=2,
        ),
        user=AuthenticatedUser(
        email="trader@example.com",
        role="user",
        ),
        service=TradingCommandService(store),
    )

    assert response.status == "PENDING"
    assert response.command_id
