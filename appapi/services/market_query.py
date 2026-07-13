"""Shared limits for browser-facing market-data queries."""

MAX_QUERY_ROWS = 10_000


def normalize_limit(limit: int) -> int:
    """Reject invalid row counts and cap valid market reads."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    return min(limit, MAX_QUERY_ROWS)
