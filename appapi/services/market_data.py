"""Compatibility entrypoint for K-line market data reads."""

from appapi.schemas.market import KLineResponse
from appapi.services.kline_reader import load_kline_data


__all__ = ["KLineResponse", "load_kline_data"]
