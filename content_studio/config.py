"""Validated environment-backed configuration for the single-user application."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://www.fxstreet.com/rss/news",
    "https://www.fxstreet.com/rss/crypto",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
]


def _as_bool(value: str | None, default: bool = True) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _bounded_float(value: str | None, default: float, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value) if value else default
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


def _bounded_int(value: str | None, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value) if value else default
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


def _configured_path(value: str | None, default: str) -> Path:
    path = Path(value or default).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    ai_provider: str
    groq_api_key: str
    groq_model: str
    gemini_api_key: str
    gemini_model: str
    database_path: Path
    rss_feeds: list[str]
    rss_timeout_seconds: float
    max_research_results: int
    market_data_enabled: bool
    request_timeout_seconds: float = 20.0
    media_storage_path: Path = PROJECT_ROOT / "data" / "generated_images"
    log_level: str = "INFO"

    @property
    def selected_api_key(self) -> str:
        if self.ai_provider == "groq":
            return self.groq_api_key
        if self.ai_provider == "gemini":
            return self.gemini_api_key
        return ""

    @property
    def selected_model(self) -> str:
        if self.ai_provider == "groq":
            return self.groq_model
        if self.ai_provider == "gemini":
            return self.gemini_model
        return "(unsupported provider)"

    @property
    def text_ai_configured(self) -> bool:
        return bool(self.selected_api_key)


def get_settings() -> Settings:
    """Read settings from environment and local .env without exposing secret values."""
    raw_feeds = os.getenv("RSS_FEEDS", "").strip()
    feeds = (
        [item.strip() for item in raw_feeds.split(",") if item.strip()]
        if raw_feeds
        else DEFAULT_RSS_FEEDS.copy()
    )
    provider = os.getenv("AI_PROVIDER", "groq").strip().lower() or "groq"
    # Preserve unsupported values so the UI/writer can report them explicitly.
    return Settings(
        ai_provider=provider,
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        groq_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip() or "openai/gpt-oss-20b",
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash",
        database_path=_configured_path(os.getenv("DATABASE_PATH"), "data/content_studio.db"),
        rss_feeds=feeds,
        rss_timeout_seconds=_bounded_float(os.getenv("RSS_TIMEOUT_SECONDS"), 12.0, 2.0, 60.0),
        max_research_results=_bounded_int(os.getenv("MAX_RESEARCH_RESULTS"), 6, 1, 15),
        market_data_enabled=_as_bool(os.getenv("BINANCE_MARKET_DATA_ENABLED"), True),
        request_timeout_seconds=_bounded_float(
            os.getenv("REQUEST_TIMEOUT_SECONDS"), 20.0, 2.0, 60.0
        ),
        media_storage_path=_configured_path(
            os.getenv("MEDIA_STORAGE_PATH"), "data/generated_images"
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
