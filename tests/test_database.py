from content_studio.database import init_db
from content_studio.repositories import (
    create_draft,
    create_workflow_run,
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