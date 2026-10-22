"""Shared typed data structures used by the initial content workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ResearchSource:
    title: str
    url: str
    publisher: str
    summary: str
    published_at: str | None = None
    retrieved_at: str = ""
    relevance_score: int = 0
    directly_relevant: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    price: str
    price_change_percent_24h: str | None = None
    retrieved_at: str = ""
    source_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchBundle:
    topic: str
    category: str
    created_at: str
    sources: list[ResearchSource] = field(default_factory=list)
    market_data: list[MarketSnapshot] = field(default_factory=list)
    suggested_topics: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "category": self.category,
            "created_at": self.created_at,
            "sources": [source.to_dict() for source in self.sources],
            "market_data": [item.to_dict() for item in self.market_data],
            "suggested_topics": self.suggested_topics,
            "warnings": self.warnings,
        }
