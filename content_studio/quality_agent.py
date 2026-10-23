"""Deterministic baseline content checks; this is not a guarantee of factual accuracy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .models import ResearchBundle

_RISK_PHRASES = (
    "guaranteed profit",
    "guaranteed returns",
    "risk-free investment",
    "100% guaranteed",
    "cannot lose",
    "sure profit",
)


@dataclass(frozen=True)
class QualityReport:
    status: str
    warnings: list[str]
    checks: list[dict[str, str | bool]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_content(draft_text: str, research: ResearchBundle) -> QualityReport:
    text = draft_text.strip()
    warnings: list[str] = []
    checks: list[dict[str, str | bool]] = []

    has_content = bool(text)
    checks.append(
        {
            "name": "non_empty_draft",
            "passed": has_content,
            "message": "Draft contains text." if has_content else "Draft is empty.",
        }
    )
    if not has_content:
        warnings.append("The draft is empty.")

    has_sources = bool(research.sources)
    checks.append(
        {
            "name": "research_sources",
            "passed": has_sources,
            "message": "Research sources are attached."
            if has_sources
            else "No research sources are attached.",
        }
    )
    if not has_sources:
        warnings.append("No research sources are attached to support factual claims.")

    normalized = text.casefold()
    risky = [phrase for phrase in _RISK_PHRASES if phrase in normalized]
    checks.append(
        {
            "name": "financial_claim_language",
            "passed": not risky,
            "message": "No configured guaranteed-return phrase detected."
            if not risky
            else "Potentially misleading guarantee language detected.",
        }
    )
    if risky:
        warnings.append(
            "Guaranteed returns language detected: "
            + ", ".join(risky)
            + "."
        )

    source_urls = [source.url for source in research.sources if source.url]
    cites_source = any(url in text for url in source_urls)
    checks.append(
        {
            "name": "source_attribution",
            "passed": cites_source,
            "message": "At least one supplied source URL appears in the draft."
            if cites_source
            else "The draft does not include a supplied source URL.",
        }
    )
    if not cites_source:
        warnings.append(
            "The draft does not include a supplied source URL; confirm source attribution before publication."
        )

    if not has_content or not has_sources or risky:
        status = "failed"
    elif warnings:
        status = "passed_with_warnings"
    else:
        status = "passed"
    return QualityReport(status=status, warnings=warnings, checks=checks)
