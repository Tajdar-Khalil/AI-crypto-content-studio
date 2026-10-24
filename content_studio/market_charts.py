"""Fetch validated Binance Spot/USDT-M Futures market data and render factual charts."""

from __future__ import annotations

from datetime import timezone
from io import BytesIO
from typing import Literal

import matplotlib.dates as mdates
import pandas as pd
import requests
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from .models import MarketSnapshot

MarketType = Literal["spot", "futures"]
Period = Literal["24h", "7d", "30d"]
ChartType = Literal["line", "bar", "candlestick", "comparison"]

SPOT_BASE_URL = "https://data-api.binance.vision/api/v3"
FUTURES_BASE_URL = "https://fapi.binance.com/fapi/v1"
SUPPORTED_SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT")
PERIOD_SETTINGS: dict[str, tuple[str, int]] = {
    "24h": ("15m", 96),
    "7d": ("1h", 168),
    "30d": ("4h", 180),
}
KLINE_COLUMNS = (
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
    "ignore",
)


class MarketDataError(RuntimeError):
    """Raised when a market-data response is missing, invalid, or unavailable."""


def _base_url(market_type: MarketType) -> str:
    if market_type == "spot":
        return SPOT_BASE_URL
    if market_type == "futures":
        return FUTURES_BASE_URL
    raise ValueError("market_type must be 'spot' or 'futures'.")


def fetch_klines(
    symbol: str,
    market_type: MarketType = "spot",
    period: Period = "7d",
    timeout: float = 20.0,
) -> pd.DataFrame:
    """Fetch historical OHLCV candles for a supported USDT pair."""
    normalized_symbol = symbol.upper().strip()
    if normalized_symbol not in SUPPORTED_SYMBOLS:
        raise ValueError(f"Unsupported symbol: {normalized_symbol}")
    if period not in PERIOD_SETTINGS:
        raise ValueError(f"Unsupported period: {period}")

    interval, limit = PERIOD_SETTINGS[period]
    url = f"{_base_url(market_type)}/klines"
    try:
        response = requests.get(
            url,
            params={"symbol": normalized_symbol, "interval": interval, "limit": limit + 1},
            timeout=timeout,
            headers={"User-Agent": "AI-Crypto-Content-Studio/0.2"},
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise MarketDataError(
            f"Could not retrieve {market_type} candles for {normalized_symbol}: {type(exc).__name__}."
        ) from exc

    if not isinstance(payload, list) or not payload:
        raise MarketDataError(f"Binance returned no candle data for {normalized_symbol}.")

    rows = []
    for candle in payload:
        if not isinstance(candle, list) or len(candle) < 12:
            raise MarketDataError(f"Binance returned an invalid candle for {normalized_symbol}.")
        rows.append(candle[:12])

    frame = pd.DataFrame(rows, columns=KLINE_COLUMNS)
    numeric_columns = (
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_volume",
        "trades",
        "taker_buy_base_volume",
        "taker_buy_quote_volume",
    )
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["open_time"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True, errors="coerce")
    frame["close_time"] = pd.to_datetime(frame["close_time"], unit="ms", utc=True, errors="coerce")
    frame = frame.dropna(subset=["open_time", "close_time", "open", "high", "low", "close", "volume"])
    frame = frame.sort_values("open_time").drop_duplicates("open_time").reset_index(drop=True)
    # Exclude the currently forming candle so period statistics use completed candles only.
    frame = frame[frame["close_time"] <= pd.Timestamp.now(tz="UTC")].tail(limit).reset_index(drop=True)
    if frame.empty:
        raise MarketDataError(f"No valid candle rows were received for {normalized_symbol}.")
    if (frame[["open", "high", "low", "close"]] <= 0).any().any():
        raise MarketDataError(f"Binance returned a non-positive price for {normalized_symbol}.")
    if (frame["volume"] < 0).any():
        raise MarketDataError(f"Binance returned invalid volume for {normalized_symbol}.")
    return frame


def fetch_market_metrics(
    symbol: str,
    market_type: MarketType = "spot",
    timeout: float = 20.0,
) -> dict[str, str | None]:
    """Fetch current ticker metrics; futures additionally include funding and open interest."""
    normalized_symbol = symbol.upper().strip()
    if normalized_symbol not in SUPPORTED_SYMBOLS:
        raise ValueError(f"Unsupported symbol: {normalized_symbol}")
    base = _base_url(market_type)
    try:
        ticker_response = requests.get(
            f"{base}/ticker/24hr",
            params={"symbol": normalized_symbol},
            timeout=timeout,
            headers={"User-Agent": "AI-Crypto-Content-Studio/0.2"},
        )
        ticker_response.raise_for_status()
        ticker = ticker_response.json()
        if not isinstance(ticker, dict) or "lastPrice" not in ticker:
            raise MarketDataError(f"Invalid ticker response for {normalized_symbol}.")
        metrics: dict[str, str | None] = {
            "current_price": str(ticker["lastPrice"]),
            "change_24h_percent": str(ticker.get("priceChangePercent", "")) or None,
            "base_volume_24h": str(ticker.get("volume", "")) or None,
            "quote_volume_24h": str(ticker.get("quoteVolume", "")) or None,
            "trades_24h": str(ticker.get("count", "")) or None,
            "funding_rate": None,
            "open_interest": None,
            "mark_price": None,
            "index_price": None,
        }
        if market_type == "futures":
            premium_response = requests.get(
                f"{base}/premiumIndex",
                params={"symbol": normalized_symbol},
                timeout=timeout,
                headers={"User-Agent": "AI-Crypto-Content-Studio/0.2"},
            )
            premium_response.raise_for_status()
            premium = premium_response.json()
            if isinstance(premium, dict):
                metrics["funding_rate"] = str(premium.get("lastFundingRate", "")) or None
                metrics["mark_price"] = str(premium.get("markPrice", "")) or None
                metrics["index_price"] = str(premium.get("indexPrice", "")) or None
            interest_response = requests.get(
                f"{base}/openInterest",
                params={"symbol": normalized_symbol},
                timeout=timeout,
                headers={"User-Agent": "AI-Crypto-Content-Studio/0.2"},
            )
            interest_response.raise_for_status()
            interest = interest_response.json()
            if isinstance(interest, dict):
                metrics["open_interest"] = str(interest.get("openInterest", "")) or None
        return metrics
    except requests.RequestException as exc:
        raise MarketDataError(
            f"Could not retrieve {market_type} ticker metrics for {normalized_symbol}: {type(exc).__name__}."
        ) from exc


def summarize_market(
    symbol: str,
    market_type: MarketType,
    period: Period,
    frame: pd.DataFrame,
    metrics: dict[str, str | None],
) -> MarketSnapshot:
    """Create a source-linked market evidence record for the AI writing workflow."""
    if frame.empty:
        raise ValueError("Cannot summarize an empty candle series.")
    start_price = float(frame.iloc[0]["open"])
    end_price = float(frame.iloc[-1]["close"])
    period_change = ((end_price - start_price) / start_price) * 100 if start_price else 0.0
    source_url = (
        f"{_base_url(market_type)}/klines"
        f"?symbol={symbol.upper()}&interval={PERIOD_SETTINGS[period][0]}&limit={PERIOD_SETTINGS[period][1]}"
    )
    return MarketSnapshot(
        symbol=symbol.upper(),
        price=metrics.get("current_price") or str(end_price),
        price_change_percent_24h=metrics.get("change_24h_percent"),
        retrieved_at=pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        source_url=source_url,
        market_type=market_type,
        period=period,
        period_start_price=f"{start_price:.12g}",
        period_end_price=f"{end_price:.12g}",
        period_change_percent=f"{period_change:.6f}",
        period_base_volume=f"{float(frame['volume'].sum()):.12g}",
        period_quote_volume=f"{float(frame['quote_volume'].sum()):.12g}",
        trades_24h=metrics.get("trades_24h"),
        period_trades=str(int(frame["trades"].sum())),
        funding_rate=metrics.get("funding_rate"),
        open_interest=metrics.get("open_interest"),
        mark_price=metrics.get("mark_price"),
        index_price=metrics.get("index_price"),
        data_points=str(len(frame)),
    )


def render_market_chart(
    frame: pd.DataFrame,
    symbol: str,
    market_type: MarketType,
    period: Period,
    chart_type: ChartType = "line",
    comparison_frames: dict[str, pd.DataFrame] | None = None,
) -> bytes:
    """Render a chart as a PNG using only the supplied, validated market data."""
    if frame.empty:
        raise ValueError("Cannot chart an empty data frame.")
    if chart_type not in {"line", "bar", "candlestick", "comparison"}:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    fig = Figure(figsize=(10, 5.5), constrained_layout=True)
    FigureCanvasAgg(fig)
    ax = fig.subplots()
    title = f"{symbol.upper()} {market_type.title()} · {period}"
    if chart_type == "line":
        ax.plot(frame["open_time"], frame["close"], linewidth=2, label="Close price")
        ax.set_ylabel("Price (USDT)")
    elif chart_type == "bar":
        changes = frame["close"].pct_change().fillna(0) * 100
        ax.bar(frame["open_time"], changes, width=0.025 if period == "24h" else 0.08)
        ax.axhline(0, linewidth=0.8)
        ax.set_ylabel("Price change per candle (%)")
    elif chart_type == "candlestick":
        dates = mdates.date2num(frame["open_time"].dt.to_pydatetime())
        if len(dates) > 1:
            candle_width = max((dates[-1] - dates[0]) / len(dates) * 0.65, 0.0005)
        else:
            candle_width = 0.02
        for date_value, row in zip(dates, frame.itertuples(index=False), strict=False):
            upward = row.close >= row.open
            ax.vlines(date_value, row.low, row.high, linewidth=0.8)
            body_bottom = min(row.open, row.close)
            body_height = max(abs(row.close - row.open), max(row.close * 0.00001, 1e-12))
            ax.add_patch(
                Rectangle(
                    (date_value - candle_width / 2, body_bottom),
                    candle_width,
                    body_height,
                    fill=not upward,
                    linewidth=0.8,
                )
            )
        ax.set_ylabel("Price (USDT)")
        ax.xaxis_date()
    else:
        datasets = comparison_frames or {symbol.upper(): frame}
        for comparison_symbol, comparison_frame in datasets.items():
            if comparison_frame.empty:
                continue
            baseline = float(comparison_frame.iloc[0]["close"])
            if baseline <= 0:
                continue
            normalized = comparison_frame["close"] / baseline * 100
            ax.plot(
                comparison_frame["open_time"],
                normalized,
                linewidth=1.8,
                label=comparison_symbol.upper(),
            )
        ax.set_ylabel("Indexed price (start = 100)")
        ax.axhline(100, linewidth=0.8, linestyle="--")
        ax.legend(loc="best")
        title = f"Crypto performance comparison · {market_type.title()} · {period}"

    ax.set_title(title)
    ax.set_xlabel("Time (UTC)")
    ax.grid(True, alpha=0.25)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d\n%H:%M", tz=timezone.utc))
    fig.autofmt_xdate()
    output = BytesIO()
    fig.savefig(output, format="png", dpi=150, bbox_inches="tight")
    return output.getvalue()


def market_fact_lines(snapshot: MarketSnapshot) -> list[str]:
    """Format validated market facts for inclusion in a content draft."""
    lines = [
        f"{snapshot.symbol} ({snapshot.market_type or 'spot'}, {snapshot.period or 'period not set'}):",
        f"- Latest reported price: {snapshot.price} USDT",
    ]
    if snapshot.price_change_percent_24h is not None:
        lines.append(f"- 24-hour change: {snapshot.price_change_percent_24h}%")
    if snapshot.period_start_price and snapshot.period_end_price and snapshot.period_change_percent:
        lines.append(
            f"- Period open-to-close change: {snapshot.period_change_percent}% "
            f"(start {snapshot.period_start_price} USDT; end {snapshot.period_end_price} USDT)"
        )
    if snapshot.period_base_volume:
        lines.append(f"- Base-asset volume over retrieved candles: {snapshot.period_base_volume}")
    if snapshot.period_quote_volume:
        lines.append(f"- Quote volume over retrieved candles: {snapshot.period_quote_volume} USDT")
    if snapshot.trades_24h is not None:
        lines.append(f"- Reported trades in the last 24 hours: {snapshot.trades_24h}")
    if snapshot.period_trades is not None:
        lines.append(f"- Trades in retrieved historical candles: {snapshot.period_trades}")
    if snapshot.funding_rate is not None:
        try:
            funding_percent = float(snapshot.funding_rate) * 100
            lines.append(
                f"- Latest reported futures funding rate: {snapshot.funding_rate} raw decimal "
                f"({funding_percent:.6f}% per funding interval, as reported by Binance)"
            )
        except ValueError:
            lines.append(f"- Latest reported futures funding rate (raw provider value): {snapshot.funding_rate}")
    if snapshot.open_interest is not None:
        lines.append(f"- Futures open interest: {snapshot.open_interest}")
    if snapshot.mark_price is not None:
        lines.append(f"- Futures mark price: {snapshot.mark_price} USDT")
    if snapshot.index_price is not None:
        lines.append(f"- Futures index price: {snapshot.index_price} USDT")
    lines.extend(
        [
            f"- Data points: {snapshot.data_points or 'not recorded'}",
            f"- Retrieved at (UTC): {snapshot.retrieved_at}",
            f"- Source: {snapshot.source_url}",
        ]
    )
    return lines
