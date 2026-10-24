"""Content-first visual agent: plan, render, and validate visuals against the written post."""

from __future__ import annotations

import re
import textwrap
from io import BytesIO
from typing import Any

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch

from .config import Settings
from .market_charts import (
    fetch_klines,
    fetch_market_metrics,
    render_market_chart,
    summarize_market,
)
from .models import MarketSnapshot, ResearchBundle

_ASSET_PATTERNS = {
    "BTCUSDT": r"\b(?:BTCUSDT|BTC|BITCOIN)\b",
    "ETHUSDT": r"\b(?:ETHUSDT|ETH|ETHEREUM)\b",
    "BNBUSDT": r"\b(?:BNBUSDT|BNB|BINANCE\s+COIN)\b",
    "SOLUSDT": r"\b(?:SOLUSDT|SOL|SOLANA)\b",
    "XRPUSDT": r"\b(?:XRPUSDT|XRP|RIPPLE)\b",
}
_MARKET_TERMS = (
    "price", "price action", "price trend", "price movement", "market data",
    "market performance", "trading", "spot", "futures", "perpetual",
    "candlestick", "ohlc", "volume", "liquidity", "open interest",
    "funding rate", "returns", "performance", "turnover", "price change",
)
_VOLUME_TERMS = ("volume", "trading activity", "turnover", "trade count")
_PIE_TERMS = ("volume share", "share of volume", "volume distribution", "volume composition")
_SCATTER_TERMS = ("volume vs change", "volume versus change", "activity vs movement", "scatter plot")


def _body_without_sources(post_text: str) -> str:
    """Return the post body without bibliography lines so references do not drive planning."""
    lines: list[str] = []
    for line in post_text.splitlines():
        if re.match(r"^\s{0,3}#{0,3}\s*(sources|references|citations)\b", line, re.IGNORECASE):
            break
        lines.append(line)
    body = "\n".join(lines)
    body = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", body)
    body = re.sub(r"https?://\S+", "", body)
    return body


def _contains_term(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(term in lowered for term in terms)


def _symbols_in_post(post_text: str) -> list[str]:
    """Return supported pairs explicitly mentioned in the post, in order of appearance."""
    body = _body_without_sources(post_text)
    found: list[tuple[int, str]] = []
    for symbol, pattern in _ASSET_PATTERNS.items():
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            found.append((match.start(), symbol))
    return [symbol for _, symbol in sorted(found)]


def _period_from_text(text: str, default_period: str) -> str:
    lowered = text.casefold()
    if re.search(r"\b(30\s*days?|one\s+month|monthly|last\s+month)\b", lowered):
        return "30d"
    if re.search(r"\b(24\s*hours?|one\s+day|daily|today)\b", lowered):
        return "24h"
    if re.search(r"\b(7\s*days?|one\s+week|weekly|this\s+week|last\s+week)\b", lowered):
        return "7d"
    return default_period if default_period in {"24h", "7d", "30d"} else "7d"


def plan_visuals(
    post_text: str,
    preferred_market_type: str = "spot",
    period: str = "7d",
) -> dict[str, Any]:
    """Choose visual types based on the written post; do not chart unrelated topics."""
    body = _body_without_sources(post_text)
    lowered = body.casefold()
    symbols = _symbols_in_post(post_text)
    market_context = _contains_term(lowered, _MARKET_TERMS)
    chart_type: str | None = None
    reason = (
        "The infographic summarizes the written post. No market chart was selected because "
        "the post does not contain a supported crypto asset together with a market-data claim."
    )

    if symbols and market_context:
        if len(symbols) >= 2 and _contains_term(lowered, _PIE_TERMS):
            chart_type = "pie"
            reason = (
                "The post discusses the distribution of trading volume, so the chart shows each "
                "mentioned pair's share of the retrieved quote volume. This is not total crypto market share."
            )
        elif len(symbols) >= 2 and _contains_term(lowered, _SCATTER_TERMS):
            chart_type = "scatter"
            reason = (
                "The post discusses volume against price movement; the scatter plot compares those "
                "two observed measures across the assets named in the post."
            )
        elif len(symbols) >= 2:
            chart_type = "comparison"
            reason = (
                "The post mentions multiple supported assets in a market context, so the chart compares "
                "their indexed price performance using the same selected period."
            )
        elif any(term in lowered for term in ("candlestick", "ohlc", "technical analysis")):
            chart_type = "candlestick"
            reason = "The post explicitly discusses OHLC or technical price action, so a candlestick chart is suitable."
        elif _contains_term(lowered, _VOLUME_TERMS):
            chart_type = "volume"
            reason = "The post discusses volume or trading activity, so the chart displays observed quote volume from the selected candles."
        elif any(term in lowered for term in ("futures", "spot trading")):
            chart_type = "candlestick"
            reason = "The post discusses spot/futures trading mechanics, so an OHLC candlestick chart is suitable."
        else:
            chart_type = "line"
            reason = "The post discusses a price trend, so a line chart is the clearest matching visual."

    market_type = preferred_market_type if preferred_market_type in {"spot", "futures"} else "spot"
    if re.search(r"\b(futures|perpetual|funding rate|open interest|mark price)\b", lowered):
        market_type = "futures"
    elif re.search(r"\bspot\b", lowered):
        market_type = "spot"

    selected_period = _period_from_text(body, period)
    return {
        "chart_needed": chart_type is not None,
        "chart_type": chart_type,
        "symbols": symbols,
        "market_type": market_type,
        "period": selected_period,
        "reason": reason,
        "infographic_needed": bool(post_text.strip()),
    }


def _render_special_chart(
    frames: dict[str, Any],
    chart_type: str,
    market_type: str,
    period: str,
) -> bytes:
    """Render pie/scatter views from real, validated Binance candle data."""
    fig = Figure(figsize=(10, 5.7), constrained_layout=True)
    FigureCanvasAgg(fig)
    ax = fig.subplots()
    labels = list(frames)
    if len(labels) < 2:
        raise ValueError(f"{chart_type} charts need at least two assets explicitly present in the post.")

    if chart_type == "pie":
        values = [float(frames[symbol]["quote_volume"].sum()) for symbol in labels]
        if any(value < 0 for value in values) or sum(values) <= 0:
            raise ValueError("Cannot build a volume-share pie chart from invalid or zero-volume data.")
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90, pctdistance=0.72)
        ax.axis("equal")
        ax.set_title(
            f"Share of retrieved quote volume · Selected USDT pairs · {market_type.title()} · {period}"
        )
    elif chart_type == "scatter":
        for symbol in labels:
            frame = frames[symbol]
            first_open = float(frame.iloc[0]["open"])
            last_close = float(frame.iloc[-1]["close"])
            change = ((last_close - first_open) / first_open) * 100 if first_open else 0.0
            quote_volume = float(frame["quote_volume"].sum())
            ax.scatter(quote_volume, change, s=80)
            ax.annotate(symbol, (quote_volume, change), xytext=(5, 5), textcoords="offset points")
        ax.axhline(0, linewidth=0.8, linestyle="--")
        ax.set_xlabel("Quote volume over retrieved candles (USDT)")
        ax.set_ylabel("Open-to-close price change (%)")
        ax.set_title(
            f"Price change vs. quote volume · Selected USDT pairs · {market_type.title()} · {period}"
        )
        ax.grid(True, alpha=0.25)
    else:
        raise ValueError(f"Unsupported special chart type: {chart_type}")

    output = BytesIO()
    fig.savefig(output, format="png", dpi=150, bbox_inches="tight")
    return output.getvalue()


def render_post_infographic(
    post_text: str,
    topic: str,
    source_count: int = 0,
    retrieved_at: str = "",
) -> bytes:
    """Render a readable infographic summary using key points already present in the post."""
    body = _body_without_sources(post_text)
    raw_lines = [line.strip() for line in body.splitlines() if line.strip()]
    title = topic.strip() or "Content summary"
    for line in raw_lines:
        heading = re.sub(r"^#{1,6}\s*", "", line).strip()
        if line.startswith("#") and heading:
            title = re.sub(r"[*_]", "", heading)
            break

    bullet_points: list[str] = []
    for line in raw_lines:
        if re.match(r"^\s*[-*•]\s+", line):
            clean = re.sub(r"^\s*[-*•]\s+", "", line)
            clean = re.sub(r"[*_]", "", clean)
            clean = re.sub(r"\s+", " ", clean).strip()
            if len(clean) >= 18 and clean not in bullet_points:
                bullet_points.append(clean)

    if len(bullet_points) < 3:
        plain_text = re.sub(r"^\s{0,3}#{1,6}\s*", "", body, flags=re.MULTILINE)
        plain_text = re.sub(r"[*_]", "", plain_text)
        sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", plain_text))
        for sentence in sentences:
            clean = sentence.strip(" -•\t")
            if len(clean) >= 28 and clean not in bullet_points:
                bullet_points.append(clean)
            if len(bullet_points) >= 3:
                break

    if not bullet_points:
        cleaned = re.sub(r"[*_]", "", re.sub(r"\s+", " ", body)).strip()
        bullet_points = [cleaned[:240] or "Review the written post for its key message."]

    bullet_points = bullet_points[:3]
    fig = Figure(figsize=(11, 7), facecolor="#0B1020")
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(
        0.07, 0.93, "CONTENT-ALIGNED INFOGRAPHIC",
        color="#8BE9FD", fontsize=10, fontweight="bold", va="top",
    )
    ax.text(
        0.07, 0.87, textwrap.fill(title, width=48),
        color="#F8FAFC", fontsize=21, fontweight="bold", va="top",
    )
    ax.text(
        0.07, 0.77, "Key points taken from the generated post",
        color="#CBD5E1", fontsize=11, va="top",
    )

    card_top = 0.70
    card_height = 0.145
    card_gap = 0.025
    for index, point in enumerate(bullet_points, start=1):
        y = card_top - (index - 1) * (card_height + card_gap)
        card = FancyBboxPatch(
            (0.06, y - card_height), 0.88, card_height,
            boxstyle="round,pad=0.012,rounding_size=0.018",
            facecolor="#151D32", edgecolor="#334155", linewidth=1.0,
        )
        ax.add_patch(card)
        ax.text(
            0.085, y - 0.038, f"{index:02d}",
            color="#8BE9FD", fontsize=13, fontweight="bold", va="top",
        )
        wrapped = textwrap.fill(point, width=82, max_lines=3, placeholder="…")
        ax.text(
            0.145, y - 0.032, wrapped,
            color="#F1F5F9", fontsize=10.5, va="top", linespacing=1.35,
        )

    footer = f"Evidence sources attached to post: {source_count}"
    if retrieved_at:
        footer += f"  •  Research retrieved: {retrieved_at}"
    ax.text(0.07, 0.055, footer, color="#94A3B8", fontsize=8.5, va="bottom")
    ax.text(
        0.93, 0.055, "AI CRYPTO CONTENT STUDIO",
        color="#8BE9FD", fontsize=8, fontweight="bold", ha="right", va="bottom",
    )
    output = BytesIO()
    fig.savefig(output, format="png", dpi=160, facecolor=fig.get_facecolor())
    return output.getvalue()


def _validation_checks(
    post_text: str,
    plan: dict[str, Any],
    snapshots: list[MarketSnapshot],
) -> list[dict[str, str | bool]]:
    body = _body_without_sources(post_text)
    mentioned = set(_symbols_in_post(body))
    intended = plan.get("symbols", [])
    has_matching_asset = bool(intended) and all(symbol in mentioned for symbol in intended)
    checks: list[dict[str, str | bool]] = [{
        "name": "visual_symbols_match_post",
        "passed": has_matching_asset,
        "message": "Every charted asset is mentioned in the post."
        if has_matching_asset else "A charted asset is not supported by the post text.",
    }]
    source_valid = bool(snapshots) and all(item.source_url and item.retrieved_at for item in snapshots)
    checks.append({
        "name": "market_data_has_source_and_timestamp",
        "passed": source_valid,
        "message": "Chart data has source URLs and retrieval timestamps."
        if source_valid else "One or more chart data records lack a source URL or timestamp.",
    })
    if plan.get("chart_type") in {"comparison", "pie", "scatter"}:
        enough_assets = len(snapshots) >= 2
        checks.append({
            "name": "multi_asset_chart_has_multiple_series",
            "passed": enough_assets,
            "message": "The selected chart has at least two explicit asset data series."
            if enough_assets else "This chart type needs at least two valid asset series.",
        })
    return checks


def generate_visual_package(
    post_text: str,
    topic: str,
    research: ResearchBundle,
    settings: Settings,
    preferred_market_type: str = "spot",
    period: str = "7d",
) -> dict[str, Any]:
    """Generate post-aligned visuals, validate their evidence, and retry a safer plan once."""
    plan = plan_visuals(post_text, preferred_market_type, period)
    warnings: list[str] = []
    chart_png: bytes | None = None
    snapshots: list[MarketSnapshot] = []
    validation: list[dict[str, str | bool]] = []
    attempts = 0

    if plan["chart_needed"] and not settings.market_data_enabled:
        warnings.append(
            "Market chart generation is disabled by BINANCE_MARKET_DATA_ENABLED. "
            "The infographic remains available."
        )
        plan = {
            **plan,
            "chart_needed": False,
            "chart_type": None,
            "reason": (
                "Market data is disabled in application settings, so no live chart was requested. "
                "The infographic still summarizes the written post."
            ),
        }

    if plan["chart_needed"]:
        for attempt in range(2):
            attempts = attempt + 1
            frames: dict[str, Any] = {}
            attempt_snapshots: list[MarketSnapshot] = []
            try:
                for symbol in plan["symbols"]:
                    frame = fetch_klines(
                        symbol,
                        market_type=plan["market_type"],
                        period=plan["period"],
                        timeout=settings.request_timeout_seconds,
                    )
                    metrics = fetch_market_metrics(
                        symbol,
                        market_type=plan["market_type"],
                        timeout=settings.request_timeout_seconds,
                    )
                    frames[symbol] = frame
                    attempt_snapshots.append(
                        summarize_market(symbol, plan["market_type"], plan["period"], frame, metrics)
                    )

                validation = _validation_checks(post_text, plan, attempt_snapshots)
                if not all(bool(check["passed"]) for check in validation):
                    raise ValueError("The visual evidence checks found a mismatch.")
                chart_type = plan["chart_type"]
                primary_symbol = plan["symbols"][0]
                if chart_type in {"pie", "scatter"}:
                    chart_png = _render_special_chart(
                        frames, chart_type, plan["market_type"], plan["period"]
                    )
                else:
                    chart_png = render_market_chart(
                        frames[primary_symbol],
                        primary_symbol,
                        plan["market_type"],
                        plan["period"],
                        chart_type,
                        comparison_frames=frames if chart_type == "comparison" else None,
                    )
                snapshots = attempt_snapshots
                break
            except Exception as exc:
                chart_png = None
                snapshots = []
                if attempt == 0:
                    warnings.append(
                        "The visual agent could not validate its first plan. It automatically "
                        "replanned once using a simpler single-asset chart and rechecked the evidence."
                    )
                    original_symbols = plan["symbols"]
                    plan = {
                        **plan,
                        "symbols": original_symbols[:1],
                        "chart_type": "line",
                        "chart_needed": bool(original_symbols),
                        "reason": (
                            "Automatic fallback: a single-asset price trend was selected after the "
                            "multi-asset visual failed validation or retrieval."
                        ),
                    }
                    if not plan["symbols"]:
                        break
                else:
                    warnings.append(
                        f"No market chart was published to the package because live data or validation "
                        f"failed ({type(exc).__name__}). The post and infographic remain available."
                    )
                    validation = [{
                        "name": "chart_generation",
                        "passed": False,
                        "message": "No chart was included because its live data could not be validated.",
                    }]
                    break

    infographic_png: bytes | None = None
    try:
        infographic_png = render_post_infographic(
            post_text,
            topic,
            source_count=len(research.sources),
            retrieved_at=research.created_at,
        )
    except Exception as exc:
        warnings.append(f"The infographic could not be rendered ({type(exc).__name__}).")

    if not plan["chart_needed"]:
        validation = [{
            "name": "chart_relevance",
            "passed": True,
            "message": "No market chart was generated because the post did not justify a supported market chart.",
        }]

    status = "passed_with_warnings" if warnings else "passed"
    slug = re.sub(r"[^a-z0-9]+", "_", topic.casefold()).strip("_")[:60] or "content"
    return {
        "plan": plan,
        "chart_png": chart_png,
        "chart_filename": f"{slug}_{plan.get('chart_type') or 'visual'}_{plan.get('period')}.png",
        "infographic_png": infographic_png,
        "infographic_filename": f"{slug}_infographic.png",
        "snapshots": [item.to_dict() for item in snapshots],
        "warnings": warnings,
        "validation": {
            "status": status,
            "attempts": attempts,
            "checks": validation,
        },
    }
