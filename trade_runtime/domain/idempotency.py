"""Deterministic idempotency helpers for durable trading commands."""

import hashlib
import json
from typing import Any


class IdempotencyConflictError(ValueError):
    """Raised when one idempotency key is reused for another command."""


def payload_hash(payload: dict[str, Any]) -> str:
    """Return the stable SHA-256 fingerprint used for key reuse checks."""
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_idempotency_reuse(existing_hash: str, requested_hash: str) -> None:
    """Reject reuse when the persisted and requested commands differ."""
    if existing_hash != requested_hash:
        raise IdempotencyConflictError(
            "idempotency key was already used with a different payload"
        )
