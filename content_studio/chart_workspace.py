"""Streamlit workspace for live market charts and attaching verified facts to research."""

from __future__ import annotations

import streamlit as st

from .config import Settings
from .market_charts import (
    MarketDataError,
    fetch_klines,
    fetch_market_metrics,
    market_fact_lines,
    render_market_chart,
    summarize_market,
)
from .models import MarketSnapshot

ASSET_LABELS = {
    "BTCUSDT": "Bitcoin (BTC/USDT)",
    "ETHUSDT": "Ethereum (ETH/USDT)",
    "BNBUSDT": "BNB (BNB/USDT)",
    "SOLUSDT": "Solana (SOL/USDT)",
    "XRPUSDT": "XRP (XRP/USDT)",
}


def render_market_chart_workspace(settings: Settings) -> None:
    """Render an interactive Spot/Futures chart workspace."""
    st.divider()
    st.header("Market charts and verified facts")
    st.caption(
        "Charts use Binance public market data. This workspace does not place trades or connect to your trading account. Market data is evidence, not a price prediction or trading instruction."
    )

    left, middle, right = st.columns(3)
    with left:
        market_type = st.selectbox("Market", ["spot", "futures"], format_func=str.title, key="chart_market_type")
    with middle:
        symbol = st.selectbox(
            "Asset",
            list(ASSET_LABELS),
            format_func=lambda value: ASSET_LABELS[value],
            key="chart_symbol",
        )
    with right:
        period = st.selectbox("Historical period", ["24h", "7d", "30d"], index=1, key="chart_period")

    chart_type = st.selectbox(
        "Chart type",
        ["line", "bar", "volume", "candlestick", "comparison"],
        format_func=lambda value: {
            "line": "Line — price trend",
            "bar": "Bar — per-candle price change",
            "volume": "Volume bars — quote volume",
            "candlestick": "Candlestick — OHLC",
            "comparison": "Comparison — relative performance",
        }[value],
        key="chart_type",
    )

    if st.button("Fetch market data and create chart", type="primary", key="fetch_market_chart"):
        try:
            with st.spinner(f"Fetching real {market_type} data from Binance…"):
                symbols = list(ASSET_LABELS) if chart_type == "comparison" else [symbol]
                frames = {
                    item: fetch_klines(
                        item,
                        market_type=market_type,
                        period=period,
                        timeout=settings.request_timeout_seconds,
                    )
                    for item in symbols
                }
                metrics = {
                    item: fetch_market_metrics(
                        item,
                        market_type=market_type,
                        timeout=settings.request_timeout_seconds,
                    )
                    for item in symbols
                }
                snapshots = {
                    item: summarize_market(item, market_type, period, frames[item], metrics[item])
                    for item in symbols
                }
                png = render_market_chart(
                    frames[symbol],
                    symbol,
                    market_type,
                    period,
                    chart_type,
                    comparison_frames=frames if chart_type == "comparison" else None,
                )
            st.session_state["market_chart_png"] = png
            st.session_state["market_chart_snapshots"] = {
                item: snapshot.to_dict() for item, snapshot in snapshots.items()
            }
            st.session_state["market_chart_selection"] = {
                "market_type": market_type,
                "symbol": symbol,
                "period": period,
                "chart_type": chart_type,
            }
            st.success("Chart and market facts generated from Binance responses.")
        except (MarketDataError, ValueError) as exc:
            st.session_state.pop("market_chart_png", None)
            st.session_state.pop("market_chart_snapshots", None)
            st.error(str(exc))
        except Exception as exc:
            st.session_state.pop("market_chart_png", None)
            st.session_state.pop("market_chart_snapshots", None)
            st.error(f"Chart generation failed ({type(exc).__name__}). No substitute data was used.")

    png = st.session_state.get("market_chart_png")
    snapshots_data = st.session_state.get("market_chart_snapshots")
    if png and snapshots_data:
        st.image(png, use_container_width=True)
        selection = st.session_state.get("market_chart_selection", {})
        st.download_button(
            "Download chart PNG",
            data=png,
            file_name=(
                f"{selection.get('symbol', 'market').lower()}_"
                f"{selection.get('market_type', 'spot')}_{selection.get('period', '7d')}.png"
            ),
            mime="image/png",
            key="download_market_chart",
        )

        st.subheader("Verified market facts")
        fact_rows = []
        for snapshot_data in snapshots_data.values():
            snapshot = MarketSnapshot(**snapshot_data)
            fact_rows.append(
                {
                    "Symbol": snapshot.symbol,
                    "Market": snapshot.market_type,
                    "Period": snapshot.period,
                    "Latest price (USDT)": snapshot.price,
                    "24h change (%)": snapshot.price_change_percent_24h,
                    "Period change (%)": snapshot.period_change_percent,
                    "Base volume": snapshot.period_base_volume,
                    "Quote volume (USDT)": snapshot.period_quote_volume,
                    "Trades (24h)": snapshot.trades_24h,
                    "Trades (selected candles)": snapshot.period_trades,
                    "Funding rate (raw decimal)": snapshot.funding_rate,
                    "Open interest (provider units)": snapshot.open_interest,
                    "Retrieved (UTC)": snapshot.retrieved_at,
                }
            )
        st.dataframe(fact_rows, use_container_width=True, hide_index=True)
        with st.expander("Show factual text for the AI draft"):
            fact_text = "\n".join(
                line
                for snapshot_data in snapshots_data.values()
                for line in market_fact_lines(MarketSnapshot(**snapshot_data))
            )
            st.text_area("Market evidence", value=fact_text, height=240, key="market_fact_text")

        research_dict = st.session_state.get("research_bundle")
        if research_dict and research_dict.get("topic"):
            if st.button("Attach these facts to current research", key="attach_market_facts"):
                existing = research_dict.setdefault("market_data", [])
                by_key = {
                    (item.get("symbol"), item.get("market_type"), item.get("period")): item
                    for item in existing
                }
                for item in snapshots_data.values():
                    snapshot = MarketSnapshot(**item)
                    by_key[(snapshot.symbol, snapshot.market_type, snapshot.period)] = item
                research_dict["market_data"] = list(by_key.values())
                warnings = research_dict.setdefault("warnings", [])
                warning = (
                    "Market facts include a timestamped Binance historical-data snapshot. "
                    "Use only the attached figures and source when describing prices or market movement."
                )
                if warning not in warnings:
                    warnings.append(warning)
                st.session_state["research_bundle"] = research_dict
                st.success(
                    "Verified market facts attached to the current research. Generate the draft again to include them."
                )
        else:
            st.info("Run topic research first, then attach these facts so the AI writer can use them in a draft.")
