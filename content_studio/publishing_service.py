"""Validate and publish an explicitly approved draft version."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .binance_square import publish_text_post
from .repositories import (
    create_publishing_attempt,
    finish_publishing_attempt,
    get_draft,
)


def publish_approved_draft(
    database_path: str | Path,
    draft_id: str,
    version_number: int,
    reviewed_text: str,
) -> dict[str, Any]:
    """Publish only the exact saved version that the owner reviewed and approved."""
    draft = get_draft(database_path, draft_id)
    if draft is None:
        raise LookupError("Saved draft not found. Reload it before publishing.")
    if int(draft["current_version_number"]) != int(version_number):
        raise ValueError("The saved draft changed. Reload and review the latest version first.")
    if draft["draft_text"] != reviewed_text:
        raise ValueError("The saved draft differs from the reviewed text. Save and review it first.")

    attempt = create_publishing_attempt(database_path, draft_id, version_number)
    try:
        result = publish_text_post(draft["draft_text"])
    except Exception as exc:
        result = {
            "success": False,
            "uncertain": True,
            "message": (
                f"The publishing operation ended unexpectedly ({type(exc).__name__}). "
                "Check Binance Square before retrying."
            ),
        }
    outcome = (
        "published" if result.get("success")
        else "uncertain" if result.get("uncertain")
        else "failed"
    )
    finish_publishing_attempt(
        database_path,
        attempt["id"],
        outcome,
        error_code=None if outcome == "published" else (
            "PUBLISHING_UNCERTAIN" if outcome == "uncertain" else "PUBLISHING_FAILED"
        ),
        error_summary=None if outcome == "published" else result.get("message"),
        external_post_id=result.get("external_post_id"),
        external_post_url=result.get("external_post_url"),
    )
    return result
