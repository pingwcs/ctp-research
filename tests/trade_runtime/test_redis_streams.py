from trade_runtime.adapters.redis_streams import (
    FencedCommandConsumer,
    InMemoryRuntimeInbox,
    RuntimeCommandEnvelope,
)


class FixedTokenAuthority:
    def __init__(self, token: int) -> None:
        self.token = token

    def current_token(self, account_id: str) -> int:
        assert account_id == "account-1"
        return self.token


def test_consumer_ignores_a_duplicate_runtime_message():
    inbox = InMemoryRuntimeInbox()
    received: list[str] = []
    consumer = FencedCommandConsumer(
        inbox=inbox,
        token_authority=FixedTokenAuthority(7),
        handle=lambda message: received.append(message.message_id),
    )
    message = RuntimeCommandEnvelope(
        message_id="message-1",
        account_id="account-1",
        fencing_token=7,
        payload={"command_id": "command-1"},
    )

    assert consumer.consume(message) is True
    assert consumer.consume(message) is False
    assert received == ["message-1"]


def test_consumer_rejects_an_old_fencing_token_before_claiming_message():
    inbox = InMemoryRuntimeInbox()
    received: list[str] = []
    consumer = FencedCommandConsumer(
        inbox=inbox,
        token_authority=FixedTokenAuthority(8),
        handle=lambda message: received.append(message.message_id),
    )

    accepted = consumer.consume(
        RuntimeCommandEnvelope(
            message_id="message-1",
            account_id="account-1",
            fencing_token=7,
            payload={"command_id": "command-1"},
        )
    )

    assert accepted is False
    assert received == []
