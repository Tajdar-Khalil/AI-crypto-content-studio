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
    market_type: str = "spot"
    period: str | None = None
    period_start_price: str | None = None
    period_end_price: str | None = None
    period_change_percent: str | None = None
    period_base_volume: str | None = None
    period_quote_volume: str | None = None
    trades_24h: str | None = None
    period_trades: str | None = None
    funding_rate: str | None = None
    open_interest: str | None = None
    mark_price: str | None = None
    index_price: str | None = None
    data_points: str | None = None

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
