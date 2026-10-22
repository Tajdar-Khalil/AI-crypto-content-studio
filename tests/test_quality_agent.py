from content_studio.models import ResearchBundle, ResearchSource
from content_studio.quality_agent import check_content


def sample_research():
    source = ResearchSource(
        title="Bitcoin documentation",
        url="https://example.com/bitcoin",
        publisher="Example",
        summary="A sample reference for testing only.",
        published_at=None,
        retrieved_at="2026-10-19T00:00:00+00:00",
        relevance_score=3,
        directly_relevant=True,
    )
    return ResearchBundle(
        topic="Bitcoin",
        category="Crypto education",
        created_at="2026-10-19T00:00:00+00:00",
        sources=[source],
    )


def test_guaranteed_profit_wording_fails_quality_check():
    report = check_content(
        "This is guaranteed profit and risk-free investment. https://example.com", sample_research()
    )
    assert report.status == "failed"
    assert any("Guaranteed returns language" in warning for warning in report.warnings)


def test_empty_draft_fails_quality_check():
    report = check_content("", sample_research())
    assert report.status == "failed"


def test_normal_draft_with_source_is_not_failed():
    draft = (
        "Bitcoin is a decentralized digital asset. Its network validates transactions through a consensus process. "
        "Market prices can change quickly and different venues may show different values. Readers should review "
        "primary sources and understand that crypto assets involve risk. This educational note is not personal "
        "financial advice. More research is useful before drawing conclusions. Sources: https://example.com/bitcoin"
    )
    report = check_content(draft, sample_research())
    assert report.status in {"passed", "passed_with_warnings"}
