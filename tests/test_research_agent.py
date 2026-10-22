from content_studio.research_agent import relevance_score, tokenize


def test_relevance_score_prefers_title_match():
    title_score = relevance_score(
        "Bitcoin ETF", "Bitcoin ETF flows rise", "Several funds reported activity."
    )
    summary_score = relevance_score(
        "Bitcoin ETF", "Funds report new activity", "Bitcoin ETF activity was discussed."
    )
    assert title_score > summary_score


def test_generic_topic_words_are_removed():
    assert "latest" not in tokenize("Latest crypto market news")
    assert "bitcoin" in tokenize("Bitcoin market analysis")


def test_unrelated_item_scores_zero():
    assert relevance_score("Bitcoin", "New solar power plant", "Renewable energy investment") == 0


def test_fetch_feed_parses_rss_without_external_feed_library(monkeypatch):
    from types import SimpleNamespace
    from content_studio.research_agent import _fetch_feed

    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel><title>Example Crypto News</title>
      <item><title>Bitcoin ETF flows update</title><link>https://example.com/bitcoin-etf</link>
        <description>Daily bitcoin ETF flow summary.</description><pubDate>Mon, 19 Oct 2026 09:00:00 GMT</pubDate>
      </item>
    </channel></rss>"""
    monkeypatch.setattr(
        "content_studio.research_agent.requests.get",
        lambda *args, **kwargs: SimpleNamespace(content=xml, raise_for_status=lambda: None),
    )
    publisher, entries = _fetch_feed("https://example.com/feed.xml", 2)
    assert publisher == "Example Crypto News"
    assert len(entries) == 1
    assert entries[0].title == "Bitcoin ETF flows update"
    assert entries[0].link == "https://example.com/bitcoin-etf"
