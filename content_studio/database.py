"""SQLite connection management and idempotent schema initialization."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('manual', 'scheduled')),
    scheduled_for TEXT,
    topic TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN (
        'pending', 'running', 'completed', 'completed_with_warnings', 'failed', 'cancelled'
    )),
    current_stage TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    error_code TEXT,
    error_summary TEXT,
    research_metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS workflow_stage_runs (
    id TEXT PRIMARY KEY,
    workflow_run_id TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN (
        'pending', 'running', 'completed', 'completed_with_warnings', 'failed', 'skipped'
    )),
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    error_code TEXT,
    error_summary TEXT,
    UNIQUE (workflow_run_id, stage, attempt_number)
);

CREATE TABLE IF NOT EXISTS research_sources (
    id TEXT PRIMARY KEY,
    workflow_run_id TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    publisher TEXT,
    published_at TEXT,
    retrieved_at TEXT NOT NULL,
    evidence_summary TEXT NOT NULL DEFAULT '',
    evidence_json TEXT NOT NULL DEFAULT '{}',
    validation_status TEXT NOT NULL CHECK (validation_status IN (
        'available', 'unavailable', 'stale', 'needs_review'
    )),
    UNIQUE (workflow_run_id, url)
);

CREATE TABLE IF NOT EXISTS drafts (
    id TEXT PRIMARY KEY,
    workflow_run_id TEXT NOT NULL UNIQUE REFERENCES workflow_runs(id) ON DELETE RESTRICT,
    current_version_number INTEGER NOT NULL CHECK (current_version_number > 0),
    approved_version_number INTEGER CHECK (
        approved_version_number IS NULL OR approved_version_number > 0
    ),
    status TEXT NOT NULL CHECK (status IN (
        'draft', 'quality_check_required', 'passed', 'passed_with_warnings',
        'failed_quality', 'pending_approval', 'rejected', 'approved', 'publishing',
        'published', 'publishing_failed', 'publishing_uncertain'
    )),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    approved_at TEXT
);

CREATE TABLE IF NOT EXISTS draft_versions (
    draft_id TEXT NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    hashtags_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(hashtags_json)),
    content_hash TEXT NOT NULL,
    quality_status TEXT NOT NULL CHECK (quality_status IN (
        'not_checked', 'passed', 'passed_with_warnings', 'failed'
    )),
    quality_warnings_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(quality_warnings_json)),
    quality_checked_at TEXT,
    change_type TEXT NOT NULL CHECK (change_type IN ('ai_generated', 'ai_regenerated', 'manual_edit')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (draft_id, version_number)
);

CREATE TABLE IF NOT EXISTS generated_images (
    id TEXT PRIMARY KEY,
    draft_id TEXT NOT NULL,
    draft_version_number INTEGER NOT NULL,
    provider TEXT NOT NULL,
    model TEXT,
    prompt TEXT NOT NULL,
    file_path TEXT,
    mime_type TEXT,
    width INTEGER CHECK (width IS NULL OR width > 0),
    height INTEGER CHECK (height IS NULL OR height > 0),
    status TEXT NOT NULL CHECK (status IN ('pending', 'generated', 'failed')),
    created_at TEXT NOT NULL,
    FOREIGN KEY (draft_id, draft_version_number)
        REFERENCES draft_versions(draft_id, version_number) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS publishing_attempts (
    id TEXT PRIMARY KEY,
    draft_id TEXT NOT NULL,
    draft_version_number INTEGER NOT NULL,
    target_platform TEXT NOT NULL CHECK (target_platform = 'binance_square'),
    status TEXT NOT NULL CHECK (status IN ('publishing', 'published', 'failed', 'uncertain')),
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    idempotency_key TEXT NOT NULL UNIQUE,
    submitted_at TEXT,
    completed_at TEXT,
    external_post_id TEXT,
    external_post_url TEXT,
    error_code TEXT,
    error_summary TEXT,
    FOREIGN KEY (draft_id, draft_version_number)
        REFERENCES draft_versions(draft_id, version_number) ON DELETE RESTRICT,
    UNIQUE (draft_id, draft_version_number, target_platform, attempt_number)
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL CHECK (json_valid(value_json)),
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_started
    ON workflow_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_status_started
    ON workflow_runs(status, started_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_scheduled_occurrence
    ON workflow_runs(scheduled_for)
    WHERE trigger_type = 'scheduled' AND scheduled_for IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_stage_runs_workflow_started
    ON workflow_stage_runs(workflow_run_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_stage_runs_status_started
    ON workflow_stage_runs(status, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sources_workflow_retrieved
    ON research_sources(workflow_run_id, retrieved_at DESC);
CREATE INDEX IF NOT EXISTS idx_drafts_status_updated
    ON drafts(status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_draft_versions_hash
    ON draft_versions(content_hash);
CREATE INDEX IF NOT EXISTS idx_images_draft_version
    ON generated_images(draft_id, draft_version_number, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_publishing_status_submitted
    ON publishing_attempts(status, submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_publishing_draft_submitted
    ON publishing_attempts(draft_id, submitted_at DESC);
"""


def get_connection(database_path: str | Path) -> sqlite3.Connection:
    """Open a configured SQLite connection and ensure its parent directory exists."""
    path = Path(database_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_or(value: object, fallback: Any) -> Any:
    try:
        return json.loads(str(value)) if value is not None else fallback
    except (TypeError, ValueError):
        return fallback


def _execute_schema(connection: sqlite3.Connection) -> None:
    # Avoid executescript's implicit pre-commit behavior so migrations can be transactional.
    for statement in SCHEMA_SQL.split(";"):
        sql = statement.strip()
        if sql:
            connection.execute(sql)


def _migrate_legacy_drafts(connection: sqlite3.Connection, legacy_rows: list[sqlite3.Row]) -> None:
    """Preserve draft records from the prototype's original denormalized schema."""
    for legacy in legacy_rows:
        record = dict(legacy)
        workflow_id = str(uuid.uuid4())
        draft_id = str(uuid.uuid4())
        created_at = str(record.get("created_at") or _now())
        updated_at = str(record.get("updated_at") or created_at)
        topic = str(record.get("topic") or "Imported draft")
        category = str(record.get("category") or "Crypto education")
        research = _json_or(record.get("research_json"), {})
        quality = _json_or(record.get("quality_json"), {})
        research = research if isinstance(research, dict) else {}
        quality = quality if isinstance(quality, dict) else {}
        body = str(record.get("draft_text") or "")
        warnings = quality.get("warnings", [])
        warnings = warnings if isinstance(warnings, list) else []
        checks = quality.get("checks", [])
        checks = checks if isinstance(checks, list) else []
        quality_status = quality.get("status")
        if quality_status not in {"passed", "passed_with_warnings", "failed"}:
            quality_status = "not_checked"
        draft_status = "failed_quality" if quality_status == "failed" else "draft"
        title = next(
            (
                re.sub(r"^\s{0,3}#{1,6}\s*", "", line).strip()[:240]
                for line in body.splitlines()
                if line.strip()
            ),
            topic[:240] or "Imported draft",
        )
        content_hash = hashlib.sha256(" ".join(body.split()).casefold().encode("utf-8")).hexdigest()
        hashtags = re.findall(r"(?<!\w)#[\w]+", body, flags=re.UNICODE)
        metadata = {
            "created_at": research.get("created_at", created_at),
            "market_data": research.get("market_data", []),
            "suggested_topics": research.get("suggested_topics", []),
            "warnings": research.get("warnings", []),
            "legacy_quality_checks": checks,
        }
        connection.execute(
            """INSERT INTO workflow_runs
            (id, trigger_type, topic, category, status, current_stage, started_at, completed_at, research_metadata_json)
            VALUES (?, 'manual', ?, ?, 'completed_with_warnings', 'legacy_import', ?, ?, ?)""",
            (
                workflow_id,
                topic,
                category,
                created_at,
                updated_at,
                json.dumps(metadata, ensure_ascii=False),
            ),
        )
        connection.execute(
            """INSERT INTO drafts
            (id, workflow_run_id, current_version_number, status, created_at, updated_at)
            VALUES (?, ?, 1, ?, ?, ?)""",
            (draft_id, workflow_id, draft_status, created_at, updated_at),
        )
        connection.execute(
            """INSERT INTO draft_versions
            (draft_id, version_number, title, body, hashtags_json, content_hash,
             quality_status, quality_warnings_json, quality_checked_at, change_type, created_at)
            VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, 'ai_generated', ?)""",
            (
                draft_id,
                title,
                body,
                json.dumps(hashtags),
                content_hash,
                quality_status,
                json.dumps(warnings, ensure_ascii=False),
                updated_at,
                created_at,
            ),
        )
        for source in research.get("sources", []):
            if not isinstance(source, dict) or not source.get("url"):
                continue
            evidence = {
                "relevance_score": source.get("relevance_score", 0),
                "directly_relevant": source.get("directly_relevant", False),
            }
            connection.execute(
                """INSERT OR IGNORE INTO research_sources
                (id, workflow_run_id, title, url, publisher, published_at, retrieved_at,
                 evidence_summary, evidence_json, validation_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'available')""",
                (
                    str(uuid.uuid4()),
                    workflow_id,
                    str(source.get("title") or "Untitled source"),
                    str(source["url"]),
                    str(source.get("publisher") or "Unknown publisher"),
                    source.get("published_at"),
                    str(source.get("retrieved_at") or created_at),
                    str(source.get("summary") or ""),
                    json.dumps(evidence, ensure_ascii=False),
                ),
            )


def init_db(database_path: str | Path) -> None:
    """Create the MVP schema or safely migrate the original prototype draft table."""
    connection = get_connection(database_path)
    try:
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if version > SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {version} is newer than this application supports ({SCHEMA_VERSION})."
            )
        existing_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        legacy_rows: list[sqlite3.Row] = []
        columns: set[str] = set()
        if "drafts" in existing_tables:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(drafts)").fetchall()}
        is_legacy = (
            "drafts" in existing_tables
            and "workflow_run_id" not in columns
            and "draft_text" in columns
        )

        if version == 0 and is_legacy:
            legacy_rows = connection.execute("SELECT * FROM drafts ORDER BY created_at").fetchall()
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("ALTER TABLE drafts RENAME TO legacy_drafts_v0")
            _execute_schema(connection)
            _migrate_legacy_drafts(connection, legacy_rows)
            connection.execute("DROP TABLE legacy_drafts_v0")
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.commit()
        elif version == 0:
            connection.execute("BEGIN IMMEDIATE")
            _execute_schema(connection)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.commit()
        else:
            _execute_schema(connection)
            connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
