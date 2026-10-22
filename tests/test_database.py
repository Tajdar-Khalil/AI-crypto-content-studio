from content_studio.database import init_db, list_drafts, save_draft, get_draft, update_draft


def test_draft_save_update_and_read(tmp_path):
    db = tmp_path / "test.sqlite3"
    init_db(db)
    draft_id = save_draft(
        db,
        topic="Bitcoin",
        category="Crypto education",
        draft_text="First draft",
        research={"topic": "Bitcoin", "sources": []},
        quality={"status": "passed", "warnings": []},
    )
    created = get_draft(db, draft_id)
    assert created is not None
    assert created["draft_text"] == "First draft"
    assert created["research"]["topic"] == "Bitcoin"
    assert update_draft(
        db,
        draft_id,
        draft_text="Edited draft",
        quality={"status": "passed_with_warnings", "warnings": ["Review source attribution"]},
    )
    updated = get_draft(db, draft_id)
    assert updated["draft_text"] == "Edited draft"
    assert updated["quality"]["status"] == "passed_with_warnings"
    assert len(list_drafts(db)) == 1
