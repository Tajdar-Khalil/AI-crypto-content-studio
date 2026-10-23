"""Coordinate research-backed writing, quality checks, and draft persistence."""

from __future__ import annotations

from typing import Any

from .config import Settings
from .database import init_db
from .models import ResearchBundle
from .quality_agent import check_content
from .repositories import (
    create_draft,
    create_workflow_run,
    finish_workflow,
    save_research_bundle,
)
from .writer_agent import generate_post


def generate_and_save_draft(
    *,
    topic: str,
    category: str,
    tone: str,
    target_length: str,
    research: ResearchBundle,
    settings: Settings,
) -> tuple[str, str, dict[str, Any]]:
    """Generate a post, check it, and persist its workflow and draft records.

    Returns the draft ID, generated text, and serialized quality report.
    Provider or persistence failures mark the workflow as failed and are re-raised.
    """
    database_path = settings.database_path
    init_db(database_path)

    workflow_id = create_workflow_run(
        database_path,
        topic=topic,
        category=category,
    )

    try:
        save_research_bundle(database_path, workflow_id, research)

        draft = generate_post(
            topic,
            category,
            tone,
            target_length,
            research,
            settings,
        )
        report = check_content(draft, research)
        report_data = report.to_dict()

        draft_id = create_draft(
            database_path,
            workflow_id=workflow_id,
            topic=topic,
            draft_text=draft,
            quality=report_data,
        )

        workflow_status = (
            "completed"
            if report.status == "passed" and not research.warnings
            else "completed_with_warnings"
        )
        finish_workflow(database_path, workflow_id, workflow_status)
        return draft_id, draft, report_data
    except Exception as exc:
        try:
            finish_workflow(
                database_path,
                workflow_id,
                "failed",
                error_code=type(exc).__name__,
                error_summary="Workflow failed; inspect application logs for details.",
            )
        except Exception:
            # Preserve the original exception if recording the failure also fails.
            pass
        raise
