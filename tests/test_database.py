from content_studio.database import init_db
from content_studio.repositories import (
    approve_draft_version,
    create_draft,
    create_publishing_attempt,
    create_workflow_run,
    finish_publishing_attempt,
    get_draft,
    list_drafts,
    update_draft,
)


def test_draft_save_update_and_read(tmp_path):
    db = tmp_path / "test.sqlite3"

    # Step 1: Create the database tables.
    init_db(db)

    # Step 2: Create a workflow for the topic.
    workflow_id = create_workflow_run(
        db,
        topic="Bitcoin",
        category="Crypto education",
    )

    # Step 3: Save a draft through the repository layer.
    draft_id = create_draft(
        db,
        workflow_id=workflow_id,
        topic="Bitcoin",
        draft_text="First draft",
        quality={
            "status": "passed",
            "warnings": [],
        },
    )

    # Step 4: Check that the saved draft can be retrieved.
    created = get_draft(db, draft_id)

    assert created is not None
    assert created["draft_text"] == "First draft"
    assert created["topic"] == "Bitcoin"
    assert created["research"]["topic"] == "Bitcoin"
    assert created["quality"]["status"] == "passed"

    # Step 5: Edit the draft.
    update_draft(
        db,
        draft_id,
        draft_text="Edited draft",
        quality={
            "status": "passed_with_warnings",
            "warnings": ["Review source attribution"],
        },
    )

    # Step 6: Confirm the edited version was saved.
    updated = get_draft(db, draft_id)

    assert updated is not None
    assert updated["draft_text"] == "Edited draft"
    assert updated["quality"]["status"] == "passed_with_warnings"
    assert updated["quality"]["warnings"] == [
        "Review source attribution"
    ]

    # Step 7: Confirm the edit created a new version.
    assert updated["current_version_number"] == 2

    # Step 8: Confirm the draft appears in the list.
    drafts = list_drafts(db)

    assert len(drafts) == 1
    assert drafts[0]["id"] == draft_id
    assert drafts[0]["topic"] == "Bitcoin"


def test_publishing_requires_approved_quality_checked_version(tmp_path):
    db = tmp_path / "publish.sqlite3"
    init_db(db)
    workflow_id = create_workflow_run(db, topic="Bitcoin", category="Crypto education")
    draft_id = create_draft(
        db,
        workflow_id=workflow_id,
        topic="Bitcoin",
        draft_text="A sourced educational post.",
        quality={"status": "passed_with_warnings", "warnings": ["Review the date."]},
    )

    try:
        create_publishing_attempt(db, draft_id, 1)
        assert False, "An unapproved version must not be publishable."
    except ValueError as exc:
        assert "not been approved" in str(exc)

    approve_draft_version(db, draft_id, 1)
    attempt = create_publishing_attempt(db, draft_id, 1)
    assert attempt["status"] == "publishing"

    try:
        create_publishing_attempt(db, draft_id, 1)
        assert False, "A conflicting in-flight attempt must be rejected."
    except ValueError as exc:
        assert "previous publishing attempt" in str(exc)

    finish_publishing_attempt(
        db,
        attempt["id"],
        "published",
        external_post_id="12345",
        external_post_url="https://www.binance.com/square/post/12345",
    )
    saved = get_draft(db, draft_id)
    assert saved is not None
    assert saved["status"] == "published"

    try:
        create_publishing_attempt(db, draft_id, 1)
        assert False, "A confirmed published post must not be duplicated."
    except ValueError as exc:
        assert "already published" in str(exc)
