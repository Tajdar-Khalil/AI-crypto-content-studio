"""Discover niche-specific, recent topic ideas from configured news feeds."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from .config import Settings
from .research_agent import _fetch_feed

_CATEGORY_TERMS: dict[str, set[str]] = {
    "Crypto market analysis": {
        "bitcoin", "ethereum", "crypto", "token", "altcoin", "market", "price",
        "volume", "exchange", "etf", "liquidity", "on-chain",
    },
    "Spot trading": {
        "spot", "bitcoin", "ethereum", "price", "volume", "order book", "liquidity",
        "exchange", "trading pair", "crypto",
    },
    "Futures and derivatives": {
        "futures", "perpetual", "derivatives", "funding rate", "open interest",
        "liquidation", "leverage", "bitcoin", "ethereum", "crypto",
    },
    "Forex and macro markets": {
        "forex", "currency", "dollar", "usd", "eur", "gbp", "yen", "fed",
        "central bank", "inflation", "interest rate", "yield", "gold", "commodities",
        "economic data", "macro",
    },
    "Finance and digital assets": {
        "finance", "bank", "payment", "tokenization", "stablecoin", "digital asset",
        "investment", "regulation", "market", "bitcoin", "ethereum", "crypto",
    },
    "Blockchain and digital-asset technology": {
        "blockchain", "protocol", "layer 2", "scaling", "wallet", "security",
        "smart contract", "defi", "web3", "token", "ethereum", "bitcoin",
    },
    "Crypto security and risk awareness": {
        "security", "hack", "exploit", "scam", "phishing", "wallet", "custody",
        "risk", "regulation", "exchange", "crypto", "bitcoin",
    },
    "Crypto education": {
        "bitcoin", "ethereum", "blockchain", "crypto", "wallet", "stablecoin",
        "defi", "trading", "digital asset", "education", "explainer",
    },
}


def _tokens(text: str) -> set[str]:
    return {word.casefold() for word in text.replace("/", " ").replace("-", " ").split() if word}


def _published_timestamp(value: str | None) -> float:
    """Parse common RSS/Atom date formats; unknown dates sort behind dated items."""
    if not value:
        return 0.0
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError, OverflowError):
            return 0.0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def discover_topic_ideas(
    category: str,
    settings: Settings,
    limit: int = 8,
) -> dict[str, Any]:
    """Return recent, category-matched headlines and any source retrieval warnings.

    This is RSS-based topic discovery, not a social-media popularity measurement.
    The UI should label suggestions as recent feed topics rather than verified global trends.
    """
    entries: list[dict[str, str | None]] = []
    warnings: list[str] = []
    for feed_url in settings.rss_feeds:
        try:
            entries.extend(_fetch_feed(feed_url, settings.rss_timeout_seconds))
        except Exception as exc:
            warnings.append(f"A configured feed could not be searched ({type(exc).__name__}).")

    deduplicated: dict[str, dict[str, str | None]] = {}
    for entry in entries:
        url = str(entry.get("url") or "").strip()
        if url:
            deduplicated.setdefault(url, entry)

    terms = _CATEGORY_TERMS.get(category, _CATEGORY_TERMS["Crypto market analysis"])
    ranked: list[tuple[int, float, dict[str, str | None]]] = []
    for entry in deduplicated.values():
        title = str(entry.get("title") or "")
        summary = str(entry.get("summary") or "")
        content = f"{title} {summary}".casefold()
        score = sum(3 for term in terms if term in title.casefold()) + sum(
            1 for term in terms if term in summary.casefold()
        )
        ranked.append((score, _published_timestamp(entry.get("published_at")), entry))

    relevant = [item for item in ranked if item[0] > 0]
    # If configured feeds have no category matches, show newest feed headlines as
    # transparent fallback suggestions; do not represent them as evidence for the topic.
    selected = relevant if relevant else ranked
    selected.sort(key=lambda item: (item[1], item[0]), reverse=True)
    topics: list[dict[str, str]] = []
    for score, _, entry in selected[: max(1, min(limit, 20))]:
        topics.append({
            "title": str(entry.get("title") or "Untitled article"),
            "url": str(entry.get("url") or ""),
            "publisher": str(entry.get("publisher") or "Unknown publisher"),
            "summary": str(entry.get("summary") or ""),
            "published_at": str(entry.get("published_at") or ""),
            "relevance_score": str(score),
        })
    if not topics and not warnings:
        warnings.append("No headlines were available from the configured RSS feeds.")
    if topics and not relevant:
        warnings.append(
            "No recent feed headline matched this niche directly; displayed suggestions are general feed headlines."
        )
    return {"topics": topics, "warnings": warnings}
