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