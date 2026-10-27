from pathlib import Path

from content_studio.config import Settings
from content_studio.topic_agent import discover_topic_ideas


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        ai_provider="groq",
        groq_api_key="",
        groq_model="openai/gpt-oss-20b",
        gemini_api_key="",
        gemini_model="gemini-3.8-flash",
        database_path=tmp_path / "content.db",
        rss_feeds=["https://example.com/feed.xml"],
        rss_timeout_seconds=2,
        max_research_results=3,
        market_data_enabled=False,
    )


def test_topic_discovery_prioritizes_niche_matched_recent_headlines(monkeypatch, tmp_path):
    entries = [
        {
            "title": "Bitcoin and Ethereum market update",
            "url": "https://example.com/crypto",
            "publisher": "Example Crypto",
            "summary": "Crypto market activity.",
            "published_at": "Sat, 24 Oct 2026 10:00:00 GMT",
        },
        {
            "title": "US dollar and Fed policy outlook",
            "url": "https://example.com/forex",
            "publisher": "Example Markets",
            "summary": "The dollar moved as traders considered interest rates.",
            "published_at": "Sat, 24 Oct 2026 09:00:00 GMT",
        },
    ]
    monkeypatch.setattr("content_studio.topic_agent._fetch_feed", lambda *args: entries)

    result = discover_topic_ideas("Forex and macro markets", make_settings(tmp_path))

    assert result["topics"]
    assert result["topics"][0]["title"] == "US dollar and Fed policy outlook"
    assert result["topics"][0]["relevance_score"] != "0"
