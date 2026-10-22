"""Core first-milestone workflow: research first, then real AI writing and saved output."""

from __future__ import annotations
from .config import Settings
from .database import save_draft
from .models import ResearchBundle
from .quality_agent import check_content
from .writer_agent import generate_post


def generate_and_save_draft(
    *,
    topic: str,
    category: str,
    tone: str,
    target_length: str,
    research: ResearchBundle,
    settings: Settings,
) -> tuple[int, str, dict]:
    draft = generate_post(topic, category, tone, target_length, research, settings)
    report = check_content(draft, research)
    draft_id = save_draft(
        settings.database_path,
        topic=topic,
        category=category,
        draft_text=draft,
        research=research.to_dict(),
        quality=report.to_dict(),
    )
    return draft_id, draft, report.to_dict()
