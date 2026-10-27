"""Orchestrate the content-first Research -> Writer -> Visuals sequence."""

from __future__ import annotations

from typing import Any

from .config import Settings
from .models import ResearchBundle
from .visual_agent import generate_visual_package
from .workflow_service import generate_and_save_draft


def generate_content_package(
    *,
    topic: str,
    category: str,
    tone: str,
    target_length: str,
    post_format: str,
    research: ResearchBundle,
    settings: Settings,
    preferred_market_type: str = "spot",
    visual_period: str = "7d",
) -> dict[str, Any]:
    """Write from research first, then pass that exact post into the visual agent.

    Visual failures do not discard the saved post. They are returned as package warnings
    so the user can still edit and download the text while fixing the visual integration.
    """
    draft_id, post_text, quality = generate_and_save_draft(
        topic=topic,
        category=category,
        tone=tone,
        target_length=target_length,
        research=research,
        settings=settings,
        post_format=post_format,
    )

    try:
        visuals = generate_visual_package(
            post_text=post_text,
            topic=topic,
            research=research,
            settings=settings,
            preferred_market_type=preferred_market_type,
            period=visual_period,
        )
    except Exception as exc:
        visuals = {
            "plan": {
                "chart_needed": False,
                "chart_type": None,
                "symbols": [],
                "market_type": preferred_market_type,
                "period": visual_period,
                "reason": "Visual generation could not complete. The written post was saved successfully.",
                "infographic_needed": False,
            },
            "chart_png": None,
            "chart_filename": "",
            "infographic_png": None,
            "infographic_filename": "",
            "snapshots": [],
            "warnings": [
                f"Visual generation failed ({type(exc).__name__}). The written post remains saved."
            ],
            "validation": {
                "status": "failed",
                "attempts": 0,
                "checks": [{
                    "name": "visual_generation",
                    "passed": False,
                    "message": "Visual generation failed; retry visuals after checking the error.",
                }],
            },
        }

    return {
        "draft_id": str(draft_id),
        "post_text": post_text,
        "quality": quality,
        "post_format": post_format,
        "visuals": visuals,
    }
