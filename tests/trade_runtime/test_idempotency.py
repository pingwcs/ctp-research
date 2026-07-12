import pytest

from trade_runtime.domain.idempotency import (
    IdempotencyConflictError,
    payload_hash,
    validate_idempotency_reuse,
)


def test_payload_hash_is_stable_when_mapping_key_order_differs():
    first = {"symbol": "rb2610", "volume": 2, "price": "3258.0"}
    second = {"price": "3258.0", "volume": 2, "symbol": "rb2610"}

    assert payload_hash(first) == payload_hash(second)


def test_reusing_an_idempotency_key_with_another_payload_is_rejected():
    original = payload_hash({"symbol": "rb2610", "volume": 2})
    replacement = payload_hash({"symbol": "rb2610", "volume": 3})

    with pytest.raises(IdempotencyConflictError, match="different payload"):
        validate_idempotency_reuse(original, replacement)
