from __future__ import annotations

from unittest.mock import Mock

import pandas as pd
import pytest

from content_studio.market_charts import (
    MarketDataError,
    fetch_klines,
    market_fact_lines,
    render_market_chart,
    summarize_market,
)


def _kline(open_time: int, open_price: str, high: str, low: str, close: str, volume: str) -> list[object]:
    return [
        open_time,
        open_price,
        high,
        low,
        close,
        volume,
        open_time + 59_999,
        "1200",
        20,
        "0.4",
        "500",
        "0",
    ]


def test_fetch_klines_parses_and_validates_response(monkeypatch: pytest.MonkeyPatch) -> None:
    response = Mock()
    response.json.return_value = [
        _kline(1_760_000_000_000, "100", "110", "95", "105", "10"),
        _kline(1_760_000_060_000, "105", "112", "103", "110", "12"),
    ]
    response.raise_for_status.return_value = None
    monkeypatch.setattr("content_studio.market_charts.requests.get", lambda *args, **kwargs: response)

    frame = fetch_klines("BTCUSDT", "spot", "24h")

    assert len(frame) == 2
    assert frame.iloc[-1]["close"] == 110
    assert str(frame.iloc[0]["open_time"].tz) == "UTC"


def test_fetch_klines_rejects_unsupported_symbol() -> None:
    with pytest.raises(ValueError, match="Unsupported symbol"):
        fetch_klines("FAKEUSDT", "spot", "7d")


def test_fetch_klines_reports_empty_provider_data(monkeypatch: pytest.MonkeyPatch) -> None:
    response = Mock()
    response.json.return_value = []
    response.raise_for_status.return_value = None
    monkeypatch.setattr("content_studio.market_charts.requests.get", lambda *args, **kwargs: response)

    with pytest.raises(MarketDataError, match="no candle data"):
        fetch_klines("BTCUSDT", "spot", "24h")


def test_summary_uses_real_candle_values_and_market_metadata() -> None:
    frame = pd.DataFrame(
        {
            "open_time": pd.to_datetime(["2026-10-01T00:00:00Z", "2026-10-01T01:00:00Z"], utc=True),
            "open": [100.0, 105.0],
            "high": [110.0, 115.0],
            "low": [95.0, 102.0],
            "close": [105.0, 110.0],
            "volume": [10.0, 12.0],
            "quote_volume": [1050.0, 1320.0],
            "trades": [20, 20],
        }
    )
    snapshot = summarize_market(
        "BTCUSDT",
        "futures",
        "7d",
        frame,
        {
            "current_price": "111",
            "change_24h_percent": "3.2",
            "funding_rate": "0.0001",
            "open_interest": "12345",
            "trades_24h": "1200",
            "mark_price": "110.9",
            "index_price": "111.1",
        },
    )

    assert snapshot.period_change_percent == "10.000000"
    assert snapshot.period_start_price == "100"
    assert snapshot.period_end_price == "110"
    assert snapshot.market_type == "futures"
    assert snapshot.funding_rate == "0.0001"
    assert snapshot.open_interest == "12345"
    assert snapshot.period_trades == "40"
    assert snapshot.trades_24h == "1200"
    assert any("10.000000%" in line for line in market_fact_lines(snapshot))
    assert any("0.010000%" in line for line in market_fact_lines(snapshot))


def test_render_line_and_candlestick_charts_as_png() -> None:
    frame = pd.DataFrame(
        {
            "open_time": pd.to_datetime(["2026-10-01T00:00:00Z", "2026-10-01T01:00:00Z"], utc=True),
            "open": [100.0, 105.0],
            "high": [110.0, 115.0],
            "low": [95.0, 102.0],
            "close": [105.0, 110.0],
            "volume": [10.0, 12.0],
            "quote_volume": [1050.0, 1320.0],
        }
    )

    line_png = render_market_chart(frame, "BTCUSDT", "spot", "24h", "line")
    candle_png = render_market_chart(frame, "BTCUSDT", "futures", "7d", "candlestick")

    assert line_png.startswith(b"\x89PNG\r\n\x1a\n")
    assert candle_png.startswith(b"\x89PNG\r\n\x1a\n")
