"""Collect configured RSS evidence and optional public Binance market snapshots."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from importlib import import_module
from typing import Any
from urllib.parse import urlparse

import requests

from .config import Settings
from .models import MarketSnapshot, ResearchBundle, ResearchSource

# Keep feedparser optional. Using import_module avoids a conditional import
# redefining the same name in the try/except branches for static type checkers.
feedparser: Any = None
try:
    feedparser = import_module("feedparser")
except ImportError:
    pass

BINANCE_MARKET_URL = "https://data-api.binance.vision/api/v3/ticker/24hr"
USER_AGENT = "AI-Crypto-Content-Studio/0.1 (+local research client)"
_GENERIC_TERMS = {
    "about",
    "analysis",
    "and",
    "for",
    "from",
    "guide",
    "latest",
    "market",
    "news",
    "price",
    "crypto",
    "cryptocurrency",
    "the",
    "to",
    "update",
    "what",
    "with",
}
_ASSET_SYMBOLS = {
    "bitcoin": "BTCUSDT",
    "btc": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "eth": "ETHUSDT",
    "solana": "SOLUSDT",
    "sol": "SOLUSDT",
    "bnb": "BNBUSDT",
    "binance coin": "BNBUSDT",
    "xrp": "XRPUSDT",
    "ripple": "XRPUSDT",
    "dogecoin": "DOGEUSDT",
    "doge": "DOGEUSDT",
    "cardano": "ADAUSDT",
    "ada": "ADAUSDT",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean_html(value: object) -> str:
    raw = str(value or "")
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.casefold()) if len(token) > 1}


def _topic_terms(topic: str) -> set[str]:
    terms = _tokens(topic) - _GENERIC_TERMS
    if not terms:
        terms = _tokens(topic)
    aliases = {"btc": "bitcoin", "eth": "ethereum", "sol": "solana", "doge": "dogecoin"}
    expanded = set(terms)
    expanded.update(aliases[term] for term in terms if term in aliases)
    for long_name, symbol in (
        ("bitcoin", "btc"),
        ("ethereum", "eth"),
        ("solana", "sol"),
        ("dogecoin", "doge"),
    ):
        if long_name in expanded:
            expanded.add(symbol)
    return expanded


def _relevance(topic_terms: set[str], title: str, summary: str) -> int:
    title_terms = _tokens(title)
    summary_terms = _tokens(summary)
    return 3 * len(topic_terms & title_terms) + len(topic_terms & summary_terms)


def tokenize(value: str) -> set[str]:
    """Return topic terms without generic words."""
    return _tokens(value) - _GENERIC_TERMS


def relevance_score(topic: str, title: str, summary: str) -> int:
    """Score an article against a topic, giving title matches more weight."""
    return _relevance(_topic_terms(topic), title, summary)


def _publisher(url: str, feed_title: str = "") -> str:
    host = urlparse(url).hostname or "Unknown publisher"
    return feed_title.strip() or host.removeprefix("www.")


def _fetch_feed(feed_url: str, timeout: float) -> list[dict[str, str | None]]:
    parsed = urlparse(feed_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("RSS feed URLs must use HTTP or HTTPS and include a hostname.")
    response = requests.get(
        feed_url,
        timeout=timeout,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
        },
    )
    response.raise_for_status()
    raw_entries: list[dict[str, object]]
    if feedparser is not None:
        parsed_feed = feedparser.parse(response.content)
        if parsed_feed.bozo and not parsed_feed.entries:
            raise ValueError("The feed could not be parsed and contained no entries.")
        feed_title = str(parsed_feed.feed.get("title", ""))
        raw_entries = [
            {
                "title": entry.get("title", "Untitled article"),
                "url": entry.get("link", ""),
                "summary": entry.get("summary", entry.get("description", "")),
                "published_at": entry.get("published", entry.get("updated", "")),
            }
            for entry in parsed_feed.entries
        ]
    else:
        # Standard-library fallback keeps source parsing testable if optional
        # feedparser is not installed.
        from xml.etree import ElementTree

        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError as exc:
            raise ValueError("The feed is not valid XML.") from exc

        def local_name(element: ElementTree.Element) -> str:
            return element.tag.rsplit("}", 1)[-1].casefold()

        def child_text(element: ElementTree.Element, *names: str) -> str:
            for descendant in element.iter():
                if descendant is element:
                    continue
                if local_name(descendant) in names and (descendant.text or "").strip():
                    return descendant.text or ""
            return ""

        feed_title = child_text(root, "title")
        item_elements = [
            element for element in root.iter() if local_name(element) in {"item", "entry"}
        ]
        raw_entries = []
        for element in item_elements:
            link = ""
            for link_element in element.iter():
                if local_name(link_element) == "link":
                    link = link_element.attrib.get("href") or (link_element.text or "").strip()
                    if link:
                        break
            raw_entries.append(
                {
                    "title": child_text(element, "title") or "Untitled article",
                    "url": link,
                    "summary": child_text(
                        element, "summary", "description", "encoded", "content"
                    ),
                    "published_at": child_text(
                        element, "published", "updated", "pubdate"
                    )
                    or None,
                }
            )

    results: list[dict[str, str | None]] = []
    for entry in raw_entries:
        link = str(entry.get("url") or "").strip()
        if not link or urlparse(link).scheme not in {"http", "https"}:
            continue
        results.append(
            {
                "title": _clean_html(entry.get("title", "Untitled article")) or "Untitled article",
                "url": link,
                "publisher": _publisher(link, feed_title),
                "summary": _clean_html(entry.get("summary", "")),
                "published_at": str(entry.get("published_at") or "").strip() or None,
            }
        )
    return results


def _collect_market_data(
    topic: str, settings: Settings, retrieved_at: str
) -> tuple[list[MarketSnapshot], list[str]]:
    if not settings.market_data_enabled:
        return [], []
    lowered = topic.casefold()
    symbols: list[str] = []
    for asset, symbol in _ASSET_SYMBOLS.items():
        if re.search(rf"\b{re.escape(asset)}\b", lowered) and symbol not in symbols:
            symbols.append(symbol)
    # Avoid duplicate API requests when both an alias and a display name are present.
    snapshots: list[MarketSnapshot] = []
    warnings: list[str] = []
    for symbol in symbols[:3]:
        try:
            response = requests.get(
                BINANCE_MARKET_URL,
                params={"symbol": symbol},
                timeout=settings.request_timeout_seconds,
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            payload = response.json()
            price = str(payload["lastPrice"])
            if not price:
                raise ValueError("Market provider returned an empty price.")
            snapshots.append(
                MarketSnapshot(
                    symbol=symbol,
                    price=price,
                    price_change_percent_24h=str(payload.get("priceChangePercent", "")) or None,
                    retrieved_at=retrieved_at,
                    source_url=f"{BINANCE_MARKET_URL}?symbol={symbol}",
                )
            )
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            warnings.append(f"Market data for {symbol} was unavailable ({type(exc).__name__}).")
    return snapshots, warnings


def collect_research(topic: str, category: str, settings: Settings) -> ResearchBundle:
    """Collect recent configured feed items relevant to a topic and optional market data."""
    clean_topic = topic.strip()
    if not clean_topic:
        raise ValueError("A research topic is required.")
    retrieved_at = _now()
    terms = _topic_terms(clean_topic)
    category_terms = _topic_terms(category)
    warnings: list[str] = []
    entries: list[dict[str, str | None]] = []

    for feed_url in settings.rss_feeds:
        try:
            entries.extend(_fetch_feed(feed_url, settings.rss_timeout_seconds))
        except (requests.RequestException, ValueError, TypeError) as exc:
            host = urlparse(feed_url).hostname or "configured feed"
            warnings.append(f"Could not retrieve {host} ({type(exc).__name__}).")

    deduplicated: dict[str, dict[str, str | None]] = {}
    for entry in entries:
        deduplicated.setdefault(str(entry["url"]), entry)

    scored: list[tuple[int, dict[str, str | None]]] = []
    suggestions: list[dict[str, str]] = []
    for entry in deduplicated.values():
        title = str(entry["title"] or "")
        summary = str(entry["summary"] or "")
        topic_score = _relevance(terms, title, summary)
        niche_score = _relevance(category_terms, title, summary)
        # Niche improves ranking only; a source must still match the requested topic
        # before it is allowed to support factual claims in the draft.
        score = topic_score + min(niche_score, 3)
        if entry["url"]:
            suggestions.append(
                {
                    "title": title,
                    "url": str(entry["url"]),
                    "publisher": str(entry["publisher"] or "Unknown publisher"),
                }
            )
        if topic_score > 0:
            scored.append((score, entry))

    scored.sort(
        key=lambda item: (item[0], str(item[1].get("published_at") or "")),
        reverse=True,
    )
    sources = [
        ResearchSource(
            title=str(entry["title"] or "Untitled article"),
            url=str(entry["url"]),
            publisher=str(entry["publisher"] or "Unknown publisher"),
            summary=str(entry["summary"] or ""),
            published_at=entry["published_at"],
            retrieved_at=retrieved_at,
            relevance_score=score,
            directly_relevant=True,
        )
        for score, entry in scored[: settings.max_research_results]
    ]

    market_data, market_warnings = _collect_market_data(clean_topic, settings, retrieved_at)
    warnings.extend(market_warnings)
    if not sources:
        warnings.append(
            "No directly relevant RSS sources were found. Headlines are suggestions, not evidence for this topic."
        )
    return ResearchBundle(
        topic=clean_topic,
        category=category,
        created_at=retrieved_at,
        sources=sources,
        market_data=market_data,
        suggested_topics=suggestions[: settings.max_research_results],
        warnings=warnings,
    )
