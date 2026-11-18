import sqlite3

import pytest

from services.audit_store import (
    read_audit_events,
    record_model_attempt,
    record_owner_override,
    verify_audit_chain,
)


def _model_result(discipline):
    return {
        "status": "METHODOLOGY NOT APPROVED",
        "discipline": discipline,
        "methodology_version": "test-unapproved",
        "ranked": [],
        "reason": "No approved methodology.",
    }


def test_model_attempt_is_persisted_and_chain_verifies(tmp_path):
    db = tmp_path / "audit.sqlite3"
    event = record_model_attempt(
        db, discipline="batting", model_result=_model_result("batting"), candidate_ids=["P1", "P2"]
    )
    events = read_audit_events(db)
    assert len(events) == 1
    assert events[0]["event_type"] == "MODEL_ATTEMPT"
    assert events[0]["event_id"] == event["event_id"]
    assert events[0]["payload"]["ranked_output_immutable"] is True
    assert verify_audit_chain(db)["valid"] is True


def test_owner_override_records_original_model_state_and_is_separate(tmp_path):
    db = tmp_path / "audit.sqlite3"
    bat = [f"BAT{i}" for i in range(10)]
    bowl = [f"BOWL{i}" for i in range(10)]
    results = {"batting": _model_result("batting"), "bowling": _model_result("bowling")}
    record_owner_override(
        db,
        overrides={"batting": bat, "bowling": bowl},
        rationales={"batting": "Review note", "bowling": "Review note"},
        model_results=results,
    )
    event = read_audit_events(db)[0]
    payload = event["payload"]
    assert event["event_type"] == "OWNER_OVERRIDE"
    assert payload["actor_identity_verified"] is False
    assert payload["model_output_modified"] is False
    assert payload["model_snapshots"]["batting"]["original_model_ranking"] == []
    assert payload["overrides"]["batting"] == bat
    assert verify_audit_chain(db)["valid"] is True


def test_invalid_override_is_rejected_without_audit_event(tmp_path):
    db = tmp_path / "audit.sqlite3"
    with pytest.raises(ValueError):
        record_owner_override(
            db,
            overrides={"batting": ["P1"], "bowling": [f"B{i}" for i in range(10)]},
            rationales={"batting": "x", "bowling": "x"},
            model_results={},
        )
    assert read_audit_events(db) == []


def test_audit_rows_cannot_be_updated_or_deleted(tmp_path):
    db = tmp_path / "audit.sqlite3"
    record_model_attempt(db, discipline="bowling", model_result=_model_result("bowling"), candidate_ids=[])
    connection = sqlite3.connect(db)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("UPDATE audit_events SET event_type='CHANGED' WHERE sequence=1")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("DELETE FROM audit_events WHERE sequence=1")
    finally:
        connection.close()
    assert verify_audit_chain(db)["valid"] is True
