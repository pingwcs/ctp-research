"""Shared value types for the live-trading domain."""

from enum import StrEnum


class Direction(StrEnum):
    """The resulting position direction of an order."""

    LONG = "LONG"
    SHORT = "SHORT"


class OffsetPolicy(StrEnum):
    """User-level policy for opening or closing a futures position."""

    OPEN = "OPEN"
    CLOSE_AUTO = "CLOSE_AUTO"
