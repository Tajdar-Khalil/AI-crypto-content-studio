from pathlib import Path

from content_studio.config import Settings
from content_studio.models import ResearchBundle, ResearchSource
from content_studio.visual_agent import (
    generate_visual_package,
    plan_visuals,
    render_post_infographic,
)


def make_settings(tmp_path: Path, **overrides) -> Settings:
    values = dict(
        ai_provider="groq",
        groq_api_key="",
        groq_model="openai/gpt-oss-20b",
        gemini_api_key="",
        gemini_model="gemini-3.8-flash",
        database_path=tmp_path / "content.db",
        rss_feeds=[],
        rss_timeout_seconds=2,
        max_research_results=3,
        market_data_enabled=False,
    )
    values.update(overrides)
    return Settings(**values)


def make_research() -> ResearchBundle:
    return ResearchBundle(
        topic="Blockchain education",
        category="Blockchain and digital-asset technology",
        created_at="2026-10-24T00:00:00+00:00",
        sources=[
            ResearchSource(
                title="Blockchain explainer",
                url="https://example.com/blockchain",
                publisher="Example",
                summary="A supplied educational source.",
                retrieved_at="2026-10-24T00:00:00+00:00",
                directly_relevant=True,
            )
        ],
    )


def test_planner_selects_line_chart_for_single_asset_price_post():
    plan = plan_visuals(
        "# Bitcoin weekly market analysis\nBitcoin (BTC) price movement over the last 7 days.",
        preferred_market_type="spot",
        period="24h",
    )

    assert plan["chart_needed"] is True
    assert plan["chart_type"] == "line"
    assert plan["symbols"] == ["BTCUSDT"]
    assert plan["period"] == "7d"


def test_planner_selects_pie_for_volume_share_between_named_assets():
    plan = plan_visuals(
        "Bitcoin (BTC) and Ethereum (ETH) trading volume share and volume distribution.",
        period="7d",
    )

    assert plan["chart_needed"] is True
    assert plan["chart_type"] == "pie"
    assert plan["symbols"] == ["BTCUSDT", "ETHUSDT"]


def test_planner_does_not_add_unrelated_market_chart_to_technology_post():
    plan = plan_visuals(
        "# How Bitcoin works\nBitcoin proof of work helps participants verify transactions "
        "and agree on the blockchain without a central operator."
    )

    assert plan["chart_needed"] is False
    assert plan["chart_type"] is None
    assert plan["infographic_needed"] is True


def test_post_infographic_is_a_png_and_uses_post_points():
    png = render_post_infographic(
        "# Bitcoin guide\n- Bitcoin transactions are recorded on a shared ledger.\n"
        "- Nodes validate blocks according to protocol rules.\n"
        "- Keys help users control access to their assets.",
        "Bitcoin guide",
        source_count=2,
        retrieved_at="2026-10-24T00:00:00+00:00",
    )

    assert png.startswith(b"\\x89PNG\\r\\n\\x1a\\n")


def test_visual_package_still_creates_infographic_when_market_chart_is_not_relevant(tmp_path):
    package = generate_visual_package(
        post_text=(
            "# Blockchain basics\nBlockchain nodes follow shared protocol rules. "
            "A public ledger can make transactions independently verifiable."
        ),
        topic="Blockchain basics",
        research=make_research(),
        settings=make_settings(tmp_path),
    )

    assert package["chart_png"] is None
    assert package["infographic_png"].startswith(b"\\x89PNG\\r\\n\\x1a\\n")
    assert package["validation"]["status"] == "passed"
