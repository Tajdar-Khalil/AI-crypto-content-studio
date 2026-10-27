import pytest

from content_studio.database import init_db
from content_studio.publishing_service import publish_approved_draft
from content_studio.repositories import (
    approve_draft_version,
    create_draft,
    create_workflow_run,
    get_draft,
    get_publishing_attempts,
)


def _approved_draft(database_path):
    init_db(database_path)
    workflow_id = create_workflow_run(
        database_path,
        topic="Bitcoin",
        category="Crypto education",
    )
    draft_id = create_draft(
        database_path,
        workflow_id=workflow_id,
        topic="Bitcoin",
        draft_text="Reviewed Bitcoin education post.",
        quality={"status": "passed", "warnings": []},
    )
    approve_draft_version(database_path, draft_id, 1)
    return draft_id


def test_publish_service_records_confirmed_success(tmp_path, monkeypatch):
    database_path = tmp_path / "publishing.sqlite3"
    draft_id = _approved_draft(database_path)
    monkeypatch.setattr(
        "content_studio.publishing_service.publish_text_post",
        lambda text: {
            "success": True,
            "uncertain": False,
            "message": "Success!",
            "external_post_id": "12345",
            "external_post_url": "https://www.binance.com/square/post/12345",
        },
    )

    result = publish_approved_draft(
        database_path,
        draft_id,
        version_number=1,
        reviewed_text="Reviewed Bitcoin education post.",
    )

    assert result["success"] is True
    saved_draft = get_draft(database_path, draft_id)
    assert saved_draft is not None
    assert saved_draft["status"] == "published"
    attempt = get_publishing_attempts(database_path, draft_id, 1)[0]
    assert attempt["external_post_id"] == "12345"
    assert attempt["status"] == "published"


def test_publish_service_rejects_text_that_was_not_reviewed(tmp_path, monkeypatch):
    database_path = tmp_path / "publishing.sqlite3"
    draft_id = _approved_draft(database_path)
    monkeypatch.setattr(
        "content_studio.publishing_service.publish_text_post",
        lambda text: pytest.fail("The adapter must not be called for mismatched text."),
    )

    with pytest.raises(ValueError, match="differs from the reviewed text"):
        publish_approved_draft(
            database_path,
            draft_id,
            version_number=1,
            reviewed_text="Different post text.",
        )
