"""Source-level contracts for the backtest UI."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_backtest_filters_use_antd_date_picker_instead_of_native_datetime_inputs():
    page = _read("appui/src/pages/BacktestPage.tsx")

    assert 'type="datetime-local"' not in page
    assert "DatePicker" in page
    assert "showTime" in page


def test_equity_trade_points_are_hidden_until_switch_enabled():
    results = _read("appui/src/pages/backtest/BacktestResults.tsx")
    chart = _read("appui/src/components/EquityChart.tsx")

    assert "useState(false)" in results
    assert "<Switch" in results
    assert "showTradeMarkers={showTradeMarkers}" in results
    assert "showTradeMarkers = false" in chart
    assert "showTradeMarkers ?" in chart


def test_equity_chart_uses_movable_time_and_equity_axes():
    chart = _read("appui/src/components/EquityChart.tsx")

    assert "createChart" in chart
    assert "LineSeries" in chart
    assert "timeVisible: true" in chart
    assert "rightPriceScale" in chart
    assert "pressedMouseMove: true" in chart
    assert "Equity" in chart
