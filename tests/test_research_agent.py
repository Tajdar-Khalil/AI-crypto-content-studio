from types import SimpleNamespace

from content_studio.research_agent import (
    _fetch_feed,
    relevance_score,
    tokenize,
)


def test_relevance_score_prefers_title_match():
    title_score = relevance_score(
        "Bitcoin ETF",
        "Bitcoin ETF flows rise",
        "Several funds reported activity.",
    )

    summary_score = relevance_score(
        "Bitcoin ETF",
        "Funds report new activity",
        "Bitcoin ETF activity was discussed.",
    )

    assert title_score > summary_score


def test_generic_topic_words_are_removed():
    terms = tokenize("Latest crypto market news")

    assert "latest" not in terms

    bitcoin_terms = tokenize("Bitcoin market analysis")

    assert "bitcoin" in bitcoin_terms


def test_unrelated_item_scores_zero():
    score = relevance_score(
        "Bitcoin",
        "New solar power plant",
        "Renewable energy investment",
    )

    assert score == 0


def test_fetch_feed_parses_rss_without_external_feed_library(monkeypatch):
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Example Crypto News</title>
        <item>
          <title>Bitcoin ETF flows update</title>
          <link>https://example.com/bitcoin-etf</link>
          <description>Daily bitcoin ETF flow summary.</description>
          <pubDate>Mon, 19 Oct 2026 09:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """

    # Force the standard-library XML parser so this test does not
    # depend on the optional feedparser package.
    monkeypatch.setattr(
        "content_studio.research_agent.feedparser",
        None,
    )

    # Simulate an HTTP response; no real network request is made.
    monkeypatch.setattr(
        "content_studio.research_agent.requests.get",
        lambda *args, **kwargs: SimpleNamespace(
            content=xml,
            raise_for_status=lambda: None,
        ),
    )

    entries = _fetch_feed(
        "https://example.com/feed.xml",
        timeout=2,
    )

    assert len(entries) == 1

    article = entries[0]

    assert article["title"] == "Bitcoin ETF flows update"
    assert article["url"] == "https://example.com/bitcoin-etf"
    assert article["publisher"] == "Example Crypto News"
    assert "bitcoin ETF flow summary" in article["summary"]
    assert article["published_at"] == "Mon, 19 Oct 2026 09:00:00 GMT"

def test_collect_research_prioritizes_selected_niche_without_accepting_unrelated_sources(monkeypatch):
    entries = [
        {
            "title": "Dollar outlook for technology companies",
            "url": "https://example.com/technology-dollar",
            "publisher": "Example",
            "summary": "Dollar outlook looks supported by technology shares.",
            "published_at": "Sat, 24 Oct 2026 08:00:00 GMT",
        },
        {
            "title": "Dollar outlook as forex markets move",
            "url": "https://example.com/forex-dollar",
            "publisher": "Example Markets",
            "summary": "Dollar outlook alongside forex and macro markets.",
            "published_at": "Sat, 24 Oct 2026 07:00:00 GMT",
        },
        {
            "title": "Blockchain wallet security",
            "url": "https://example.com/wallet",
            "publisher": "Example Tech",
            "summary": "A wallet security explainer.",
            "published_at": "Sat, 24 Oct 2026 09:00:00 GMT",
        },
    ]
    monkeypatch.setattr("content_studio.research_agent._fetch_feed", lambda *args: entries)
    monkeypatch.setattr(
        "content_studio.research_agent._collect_market_data",
        lambda *args: ([], []),
    )
    settings = SimpleNamespace(
        rss_feeds=["https://example.com/feed.xml"],
        rss_timeout_seconds=2,
        max_research_results=5,
        market_data_enabled=False,
        request_timeout_seconds=2,
    )

    from content_studio.research_agent import collect_research

    result = collect_research("Dollar outlook", "Forex and macro markets", settings)

    assert result.sources
    assert result.sources[0].url == "https://example.com/forex-dollar"
    assert all(source.directly_relevant for source in result.sources)
    assert all("wallet" not in source.url for source in result.sources)

