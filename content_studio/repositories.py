"""Database repository functions; UI and agents must use these instead of SQL."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .database import get_connection
from .models import ResearchBundle


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _content_hash(text: str) -> str:
    normalized = " ".join(text.split()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        cleaned = re.sub(r"^\s{0,3}#{1,6}\s*", "", line).strip()
        if cleaned:
            return cleaned[:240]
    return fallback[:240] or "Untitled draft"


def create_workflow_run(
    database_path: str | Path,
    topic: str,
    category: str,
    trigger_type: str = "manual",
    scheduled_for: str | None = None,
) -> str:
    workflow_id = str(uuid.uuid4())
    now = utc_now()
    connection = get_connection(database_path)
    try:
        connection.execute(
            """INSERT INTO workflow_runs
            (id, trigger_type, scheduled_for, topic, category, status, current_stage,
             started_at, research_metadata_json)
            VALUES (?, ?, ?, ?, ?, 'running', 'research', ?, '{}')""",
            (workflow_id, trigger_type, scheduled_for, topic.strip(), category.strip(), now),
        )
        connection.commit()
    finally:
        connection.close()
    return workflow_id


def start_stage(database_path: str | Path, workflow_id: str, stage: str) -> str:
    stage_id = str(uuid.uuid4())
    now = utc_now()
    connection = get_connection(database_path)
    try:
        row = connection.execute(
            "SELECT COALESCE(MAX(attempt_number), 0) + 1 FROM workflow_stage_runs WHERE workflow_run_id = ? AND stage = ?",
            (workflow_id, stage),
        ).fetchone()
        attempt = int(row[0])
        with connection:
            connection.execute(
                """INSERT INTO workflow_stage_runs
                (id, workflow_run_id, stage, status, attempt_number, started_at)
                VALUES (?, ?, ?, 'running', ?, ?)""",
                (stage_id, workflow_id, stage, attempt, now),
            )
            connection.execute(
                "UPDATE workflow_runs SET current_stage = ? WHERE id = ?",
                (stage, workflow_id),
            )
    finally:
        connection.close()
    return stage_id


def finish_stage(
    database_path: str | Path,
    stage_id: str,
    status: str,
    error_code: str | None = None,
    error_summary: str | None = None,
) -> None:
    if status not in {"completed", "completed_with_warnings", "failed", "skipped"}:
        raise ValueError(f"Unsupported completed stage status: {status}")
    connection = get_connection(database_path)
    try:
        with connection:
            connection.execute(
                """UPDATE workflow_stage_runs
                SET status = ?, completed_at = ?, error_code = ?, error_summary = ? WHERE id = ?""",
                (status, utc_now(), error_code, error_summary, stage_id),
            )
    finally:
        connection.close()

def finish_workflow(
    database_path: str | Path,
    workflow_id: str,
    status: str,
    error_code: str | None = None,
    error_summary: str | None = None,
) -> None:
    if status not in {"completed", "completed_with_warnings", "failed", "cancelled"}:
        raise ValueError(f"Unsupported completed workflow status: {status}")
    connection = get_connection(database_path)
    try:
        with connection:
            connection.execute(
                """UPDATE workflow_runs
                SET status = ?, completed_at = ?, error_code = ?, error_summary = ?
                WHERE id = ?""",
                (status, utc_now(), error_code, error_summary, workflow_id),
            )
    finally:
        connection.close()


def save_research_bundle(
    database_path: str | Path,
    workflow_id: str,
    research: ResearchBundle,
) -> None:
    metadata = {
        "created_at": research.created_at,
        "market_data": [item.to_dict() for item in research.market_data],
        "suggested_topics": research.suggested_topics,
        "warnings": research.warnings,
    }
    connection = get_connection(database_path)
    try:
        with connection:
            connection.execute(
                "UPDATE workflow_runs SET research_metadata_json = ? WHERE id = ?",
                (json.dumps(metadata, ensure_ascii=False), workflow_id),
            )
            for source in research.sources:
                evidence = {
                    "relevance_score": source.relevance_score,
                    "directly_relevant": source.directly_relevant,
                }
                connection.execute(
                    """INSERT INTO research_sources
                    (id, workflow_run_id, title, url, publisher, published_at, retrieved_at,
                     evidence_summary, evidence_json, validation_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'available')
                    ON CONFLICT(workflow_run_id, url) DO UPDATE SET
                      title = excluded.title,
                      publisher = excluded.publisher,
                      published_at = excluded.published_at,
                      retrieved_at = excluded.retrieved_at,
                      evidence_summary = excluded.evidence_summary,
                      evidence_json = excluded.evidence_json,
                      validation_status = 'available'""",
                    (
                        str(uuid.uuid4()),
                        workflow_id,
                        source.title,
                        source.url,
                        source.publisher,
                        source.published_at,
                        source.retrieved_at,
                        source.summary,
                        json.dumps(evidence, ensure_ascii=False),
                    ),
                )
    finally:
        connection.close()


def create_draft(
    database_path: str | Path,
    workflow_id: str,
    topic: str,
    draft_text: str,
    quality: dict[str, Any],
) -> str:
    draft_id = str(uuid.uuid4())
    now = utc_now()
    status_map = {
        "passed": "draft",
        "passed_with_warnings": "draft",
        "failed": "failed_quality",
    }
    quality_status = str(quality.get("status", "failed"))
    title = _extract_title(draft_text, topic)
    hashtags = re.findall(r"(?<!\w)#[\w]+", draft_text, flags=re.UNICODE)
    connection = get_connection(database_path)
    try:
        with connection:
            connection.execute(
                """INSERT INTO drafts
                (id, workflow_run_id, current_version_number, status, created_at, updated_at)
                VALUES (?, ?, 1, ?, ?, ?)""",
                (draft_id, workflow_id, status_map.get(quality_status, "draft"), now, now),
            )
            connection.execute(
                """INSERT INTO draft_versions
                (draft_id, version_number, title, body, hashtags_json, content_hash,
                 quality_status, quality_warnings_json, quality_checked_at, change_type, created_at)
                VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, 'ai_generated', ?)""",
                (
                    draft_id,
                    title,
                    draft_text,
                    json.dumps(hashtags),
                    _content_hash(draft_text),
                    quality_status
                    if quality_status in {"passed", "passed_with_warnings", "failed"}
                    else "not_checked",
                    json.dumps(quality.get("warnings", []), ensure_ascii=False),
                    now,
                    now,
                ),
            )
    finally:
        connection.close()
    return draft_id


def _load_research(connection: Any, workflow_row: Any, workflow_id: str) -> dict[str, Any]:
    metadata = json.loads(workflow_row["research_metadata_json"] or "{}")
    sources: list[dict[str, Any]] = []
    for row in connection.execute(
        "SELECT * FROM research_sources WHERE workflow_run_id = ? ORDER BY retrieved_at DESC",
        (workflow_id,),
    ).fetchall():
        evidence = json.loads(row["evidence_json"] or "{}")
        sources.append(
            {
                "title": row["title"],
                "url": row["url"],
                "publisher": row["publisher"] or "Unknown publisher",
                "summary": row["evidence_summary"],
                "published_at": row["published_at"],
                "retrieved_at": row["retrieved_at"],
                "relevance_score": int(evidence.get("relevance_score", 0)),
                "directly_relevant": bool(evidence.get("directly_relevant", False)),
            }
        )
    return {
        "topic": workflow_row["topic"],
        "category": workflow_row["category"],
        "created_at": metadata.get("created_at") or workflow_row["started_at"],
        "sources": sources,
        "market_data": metadata.get("market_data", []),
        "suggested_topics": metadata.get("suggested_topics", []),
        "warnings": metadata.get("warnings", []),
    }


def get_draft(database_path: str | Path, draft_id: str) -> dict[str, Any] | None:
    connection = get_connection(database_path)
    try:
        row = connection.execute(
            """SELECT d.*, v.title, v.body, v.quality_status, v.quality_warnings_json,
                      v.version_number, w.topic, w.category, w.started_at,
                      w.research_metadata_json
               FROM drafts d
               JOIN draft_versions v ON v.draft_id = d.id AND v.version_number = d.current_version_number
               JOIN workflow_runs w ON w.id = d.workflow_run_id
               WHERE d.id = ?""",
            (str(draft_id),),
        ).fetchone()
        if row is None:
            return None
        quality_warnings = json.loads(row["quality_warnings_json"] or "[]")
        return {
            "id": row["id"],
            "topic": row["topic"],
            "category": row["category"],
            "draft_text": row["body"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "current_version_number": row["current_version_number"],
            "approved_version_number": row["approved_version_number"],
            "quality": {
                "status": row["quality_status"],
                "warnings": quality_warnings,
                "checks": [],
            },
            "research": _load_research(connection, row, row["workflow_run_id"]),
        }
    finally:
        connection.close()


def list_drafts(database_path: str | Path, limit: int = 25) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 100))
    connection = get_connection(database_path)
    try:
        rows = connection.execute(
            """SELECT d.id, d.status, d.created_at, d.updated_at, d.current_version_number,
                      v.quality_status, v.quality_warnings_json, w.topic, w.category
               FROM drafts d
               JOIN draft_versions v ON v.draft_id = d.id AND v.version_number = d.current_version_number
               JOIN workflow_runs w ON w.id = d.workflow_run_id
               ORDER BY d.created_at DESC LIMIT ?""",
            (safe_limit,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "topic": row["topic"],
                "category": row["category"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "quality": {
                    "status": row["quality_status"],
                    "warnings": json.loads(row["quality_warnings_json"] or "[]"),
                    "checks": [],
                },
            }
            for row in rows
        ]
    finally:
        connection.close()


def update_draft(
    database_path: str | Path,
    draft_id: str,
    draft_text: str,
    quality: dict[str, Any],
) -> None:
    now = utc_now()
    quality_status = str(quality.get("status", "failed"))
    if quality_status not in {"passed", "passed_with_warnings", "failed"}:
        quality_status = "failed"
    warnings_json = json.dumps(quality.get("warnings", []), ensure_ascii=False)
    hashtags = re.findall(r"(?<!\w)#[\w]+", draft_text, flags=re.UNICODE)
    connection = get_connection(database_path)
    try:
        with connection:
            draft = connection.execute(
                "SELECT * FROM drafts WHERE id = ?", (str(draft_id),)
            ).fetchone()
            if draft is None:
                raise LookupError("Draft not found.")
            current = connection.execute(
                "SELECT * FROM draft_versions WHERE draft_id = ? AND version_number = ?",
                (str(draft_id), draft["current_version_number"]),
            ).fetchone()
            if current is None:
                raise RuntimeError("Current draft version is missing.")
            changed = draft_text != current["body"]
            if changed:
                next_version = int(draft["current_version_number"]) + 1
                topic_row = connection.execute(
                    "SELECT topic FROM workflow_runs WHERE id = ?", (draft["workflow_run_id"],)
                ).fetchone()
                connection.execute(
                    """INSERT INTO draft_versions
                    (draft_id, version_number, title, body, hashtags_json, content_hash,
                     quality_status, quality_warnings_json, quality_checked_at, change_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual_edit', ?)""",
                    (
                        str(draft_id),
                        next_version,
                        _extract_title(
                            draft_text, str(topic_row["topic"] if topic_row else "Draft")
                        ),
                        draft_text,
                        json.dumps(hashtags),
                        _content_hash(draft_text),
                        quality_status,
                        warnings_json,
                        now,
                        now,
                    ),
                )
                connection.execute(
                    """UPDATE drafts SET current_version_number = ?, approved_version_number = NULL,
                       approved_at = NULL, status = ?, updated_at = ? WHERE id = ?""",
                    (
                        next_version,
                        "failed_quality" if quality_status == "failed" else "draft",
                        now,
                        str(draft_id),
                    ),
                )
            else:
                connection.execute(
                    """UPDATE draft_versions SET quality_status = ?, quality_warnings_json = ?,
                       quality_checked_at = ? WHERE draft_id = ? AND version_number = ?""",
                    (
                        quality_status,
                        warnings_json,
                        now,
                        str(draft_id),
                        draft["current_version_number"],
                    ),
                )
                connection.execute(
                    "UPDATE drafts SET status = ?, updated_at = ? WHERE id = ?",
                    (
                        "failed_quality" if quality_status == "failed" else "draft",
                        now,
                        str(draft_id),
                    ),
                )
    finally:
        connection.close()


def get_publishing_attempts(
    database_path: str | Path,
    draft_id: str,
    draft_version_number: int,
) -> list[dict[str, Any]]:
    """Return publishing attempts for a specific draft version."""
    connection = get_connection(database_path)
    try:
        rows = connection.execute(
            """
            SELECT id, draft_id, draft_version_number, target_platform,
                   status, attempt_number, submitted_at, completed_at,
                   external_post_id, external_post_url,
                   error_code, error_summary
            FROM publishing_attempts
            WHERE draft_id = ?
              AND draft_version_number = ?
              AND target_platform = 'binance_square'
            ORDER BY attempt_number DESC
            """,
            (str(draft_id), int(draft_version_number)),
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        connection.close()


def create_publishing_attempt(
    database_path: str | Path,
    draft_id: str,
    draft_version_number: int,
) -> dict[str, Any]:
    """Atomically create an attempt, refusing to duplicate unresolved submissions."""
    connection = get_connection(database_path)
    attempt_id = str(uuid.uuid4())
    now = utc_now()

    try:
        connection.execute("BEGIN IMMEDIATE")

        draft = connection.execute(
            """
            SELECT current_version_number, approved_version_number, status
            FROM drafts
            WHERE id = ?
            """,
            (str(draft_id),),
        ).fetchone()

        if draft is None:
            raise LookupError("Draft not found.")

        if int(draft["current_version_number"]) != int(draft_version_number):
            raise ValueError("The draft has changed. Review the latest version first.")

        if draft["approved_version_number"] != int(draft_version_number):
            raise ValueError("This exact draft version has not been approved.")

        quality = connection.execute(
            "SELECT quality_status FROM draft_versions WHERE draft_id = ? AND version_number = ?",
            (str(draft_id), int(draft_version_number)),
        ).fetchone()
        if quality is None or quality["quality_status"] not in {"passed", "passed_with_warnings"}:
            raise ValueError("This draft version has not passed its quality check.")

        previous = connection.execute(
            """
            SELECT id, status, attempt_number
            FROM publishing_attempts
            WHERE draft_id = ?
              AND draft_version_number = ?
              AND target_platform = 'binance_square'
            ORDER BY attempt_number DESC
            LIMIT 1
            """,
            (str(draft_id), int(draft_version_number)),
        ).fetchone()

        if previous and previous["status"] in {"publishing", "uncertain", "published"}:
            raise ValueError(
                "A previous publishing attempt is unresolved or already published. "
                "Check Binance Square before proceeding."
            )

        attempt_number = (
            int(previous["attempt_number"]) + 1 if previous else 1
        )

        connection.execute(
            """
            INSERT INTO publishing_attempts (
                id, draft_id, draft_version_number, target_platform,
                status, attempt_number, idempotency_key, submitted_at
            )
            VALUES (?, ?, ?, 'binance_square', 'publishing', ?, ?, ?)
            """,
            (
                attempt_id,
                str(draft_id),
                int(draft_version_number),
                attempt_number,
                str(uuid.uuid4()),
                now,
            ),
        )

        connection.execute(
            """
            UPDATE drafts
            SET status = 'publishing', updated_at = ?
            WHERE id = ?
            """,
            (now, str(draft_id)),
        )

        connection.commit()

        return {
            "id": attempt_id,
            "draft_id": str(draft_id),
            "draft_version_number": int(draft_version_number),
            "attempt_number": attempt_number,
            "status": "publishing",
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def finish_publishing_attempt(
    database_path: str | Path,
    attempt_id: str,
    status: str,
    error_code: str | None = None,
    error_summary: str | None = None,
    external_post_id: str | None = None,
    external_post_url: str | None = None,
) -> None:
    """Persist a publishing outcome without automatically retrying."""
    if status not in {"published", "failed", "uncertain"}:
        raise ValueError(f"Unsupported publishing result: {status}")

    connection = get_connection(database_path)
    now = utc_now()

    try:
        connection.execute("BEGIN IMMEDIATE")

        attempt = connection.execute(
            """
            SELECT draft_id, status
            FROM publishing_attempts
            WHERE id = ?
            """,
            (str(attempt_id),),
        ).fetchone()

        if attempt is None:
            raise LookupError("Publishing attempt not found.")

        if attempt["status"] != "publishing":
            raise ValueError("This publishing attempt has already been finalized.")

        connection.execute(
            """
            UPDATE publishing_attempts
            SET status = ?, completed_at = ?,
                external_post_id = ?, external_post_url = ?,
                error_code = ?, error_summary = ?
            WHERE id = ?
            """,
            (
                status,
                now,
                external_post_id,
                external_post_url,
                error_code,
                error_summary,
                str(attempt_id),
            ),
        )

        draft_status = {
            "published": "published",
            "failed": "publishing_failed",
            "uncertain": "publishing_uncertain",
        }[status]

        connection.execute(
            """
            UPDATE drafts
            SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            (draft_status, now, attempt["draft_id"]),
        )

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def approve_draft_version(
    database_path: str,
    draft_id: str,
    version_number: int,
) -> None:
    """Approve the current draft version after its quality check passes."""
    connection = get_connection(database_path)

    try:
        with connection:
            draft = connection.execute(
                """
                SELECT current_version_number
                FROM drafts
                WHERE id = ?
                """,
                (draft_id,),
            ).fetchone()

            if draft is None:
                raise LookupError(f"Draft not found: {draft_id}")

            current_version = int(draft["current_version_number"])

            if current_version != version_number:
                raise ValueError(
                    "This draft has changed. Reload it before approving."
                )

            version = connection.execute(
                """
                SELECT quality_status
                FROM draft_versions
                WHERE draft_id = ? AND version_number = ?
                """,
                (draft_id, version_number),
            ).fetchone()

            if version is None:
                raise LookupError("Draft version not found.")

            quality_status = version["quality_status"]

            if quality_status not in {"passed", "passed_with_warnings"}:
                raise ValueError(
                    "Only drafts that pass the quality check can be approved."
                )

            now = utc_now()

            connection.execute(
                """
                UPDATE drafts
                SET approved_version_number = ?,
                    approved_at = ?,
                    status = 'approved',
                    updated_at = ?
                WHERE id = ?
                """,
                (version_number, now, now, draft_id),
            )
    finally:
        connection.close()
