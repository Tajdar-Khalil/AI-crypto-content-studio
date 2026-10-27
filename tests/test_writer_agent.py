from unittest.mock import Mock

import pytest

from content_studio.config import Settings
from content_studio.models import ResearchBundle, ResearchSource
from content_studio.writer_agent import (
    WriterConfigurationError,
    WriterProviderError,
    build_prompt,
    generate_post,
)


def make_settings(tmp_path, **overrides):
    values = dict(
        ai_provider="groq",
        groq_api_key="",
        groq_model="openai/gpt-oss-20b",
        gemini_api_key="",
        gemini_model="gemini-3.8-flash",
        database_path=tmp_path / "x.db",
        rss_feeds=[],
        rss_timeout_seconds=2,
        max_research_results=3,
        market_data_enabled=False,
    )
    values.update(overrides)
    return Settings(**values)


def make_research():
    source = ResearchSource(
        title="Bitcoin learning guide",
        url="https://example.com/bitcoin",
        publisher="Example",
        summary="Educational overview of Bitcoin",
        published_at="2026-10-19T00:00:00+00:00",
        retrieved_at="2026-10-19T00:00:00+00:00",
        relevance_score=5,
        directly_relevant=True,
    )
    return ResearchBundle(
        topic="Bitcoin",
        category="Crypto education",
        created_at="2026-10-19T00:00:00+00:00",
        sources=[source],
    )


def test_writer_requires_real_groq_key(tmp_path):
    settings = make_settings(tmp_path)
    with pytest.raises(WriterConfigurationError, match="GROQ_API_KEY"):
        generate_post("Bitcoin", "Crypto education", "Clear", "Short", make_research(), settings)


def test_writer_calls_groq_and_returns_real_response(monkeypatch, tmp_path):
    settings = make_settings(tmp_path, groq_api_key="test-secret")
    response = Mock(ok=True)
    response.json.return_value = {
        "choices": [{"message": {"content": "Evidence-based sample draft"}}]
    }
    monkeypatch.setattr("content_studio.writer_agent.requests.post", lambda *a, **kw: response)
    result = generate_post(
        "Bitcoin", "Crypto education", "Clear", "Short", make_research(), settings
    )
    assert result == "Evidence-based sample draft"


def test_writer_reports_groq_rate_limit(monkeypatch, tmp_path):
    settings = make_settings(tmp_path, groq_api_key="test-secret")
    response = Mock(ok=False, status_code=429, text="rate limit")
    response.headers = {"retry-after": "10"}
    response.json.return_value = {"error": {"message": "Too many requests"}}
    monkeypatch.setattr("content_studio.writer_agent.requests.post", lambda *a, **kw: response)
    with pytest.raises(WriterProviderError, match="rate or usage limit reached"):
        generate_post("Bitcoin", "Crypto education", "Clear", "Short", make_research(), settings)


def test_no_research_means_no_ai_call(tmp_path):
    settings = make_settings(tmp_path, groq_api_key="test-secret")
    empty = ResearchBundle(
        topic="Bitcoin", category="Crypto education", created_at="2026-10-19T00:00:00+00:00"
    )
    with pytest.raises(WriterConfigurationError, match="no directly relevant research sources"):
        generate_post("Bitcoin", "Crypto education", "Clear", "Short", empty, settings)

def test_writer_prompt_respects_selected_post_format():
    prompt = build_prompt(
        "Bitcoin market movement",
        "Crypto market analysis",
        "Professional and analytical",
        "Medium",
        make_research(),
        post_format="Numbered thread",
    )

    assert "Selected post format: Numbered thread" in prompt
    assert "coherent numbered sequence" in prompt
    assert "Bitcoin market movement" in prompt

