"""Coordinates research-backed draft generation without performing publishing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import Settings
from .models import ResearchBundle
from .quality_agent import check_content
from .repositories import (
    create_draft,
    create_workflow_run,
    finish_stage,
    finish_workflow,
    save_research_bundle,
    start_stage,
)
from .writer_agent import generate_post


def generate_and_save_draft(
    topic: str,
    category: str,
    tone: str,
    target_length: str,
    research: ResearchBundle,
    settings: Settings,
) -> tuple[str, str, dict[str, Any]]:
    """Generate, quality-check, and persist a draft; no publishing is performed."""
    if not research.sources:
        raise ValueError("Research sources are required before draft generation.")

    database_path: Path = settings.database_path
    workflow_id = create_workflow_run(database_path, topic, category)
    save_research_bundle(database_path, workflow_id, research)

    research_stage_id = start_stage(database_path, workflow_id, "research")
    finish_stage(database_path, research_stage_id, "completed")

    writing_stage_id = start_stage(database_path, workflow_id, "writing")
    try:
        draft_text = generate_post(topic, category, tone, target_length, research, settings)
        finish_stage(database_path, writing_stage_id, "completed")
    except Exception as exc:
        finish_stage(
            database_path,
            writing_stage_id,
            "failed",
            error_code=type(exc).__name__,
            error_summary=str(exc)[:300],
        )
        finish_workflow(
            database_path,
            workflow_id,
            "failed",
            error_code=type(exc).__name__,
            error_summary=str(exc)[:300],
        )
        raise

    quality_stage_id = start_stage(database_path, workflow_id, "quality_check")
    try:
        quality = check_content(draft_text, research).to_dict()
        finish_stage(
            database_path,
            quality_stage_id,
            "completed_with_warnings" if quality["warnings"] else "completed",
        )
        draft_id = create_draft(database_path, workflow_id, topic, draft_text, quality)
        workflow_status = (
            "completed_with_warnings" if quality["warnings"] or research.warnings else "completed"
        )
        finish_workflow(database_path, workflow_id, workflow_status)
        return draft_id, draft_text, quality
    except Exception as exc:
        finish_stage(
            database_path,
            quality_stage_id,
            "failed",
            error_code=type(exc).__name__,
            error_summary=str(exc)[:300],
        )
        finish_workflow(
            database_path,
            workflow_id,
            "failed",
            error_code=type(exc).__name__,
            error_summary=str(exc)[:300],
        )
        raise
