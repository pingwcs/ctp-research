"""Tests proving appapi forwards runtime metadata instead of owning constants."""

from appapi.services.backtest.metadata_cache import clear_metadata_cache
from appapi.services.backtest.catalog import get_metrics, get_strategies


def test_appapi_backtest_metadata_comes_from_runner(monkeypatch):
    clear_metadata_cache()
    calls = []

    def fake_invoke(command, payload=None):
        calls.append((command, payload))
        return {
            "strategies": [
                {
                    "id": "ma_cross",
                    "name": "MA Cross",
                    "description": "Runtime-owned strategy.",
                    "engine": "vnpy",
                },
            ],
            "metrics": [
                {
                    "id": "total_return",
                    "name": "Total Return",
                    "description": "Runtime-owned metric.",
                },
            ],
        }

    monkeypatch.setattr(
        "appapi.services.backtest.metadata_cache.invoke_runner",
        fake_invoke,
    )

    assert [item.id for item in get_strategies()] == ["ma_cross"]
    assert [item.id for item in get_metrics()] == ["total_return"]
    assert calls == [("metadata", None)]
    clear_metadata_cache()
