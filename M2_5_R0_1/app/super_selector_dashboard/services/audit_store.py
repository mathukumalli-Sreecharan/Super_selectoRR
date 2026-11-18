"""Local append-only, hash-chained audit store for model attempts and overrides.

This provides tamper-evident local records, not identity authentication or a
centralized authority-managed audit service.  The UI must disclose that limit.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

GENESIS_HASH = "0" * 64


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=15, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS audit_events (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            occurred_at_utc TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            event_hash TEXT NOT NULL UNIQUE
        )"""
    )
    connection.execute(
        "CREATE TRIGGER IF NOT EXISTS audit_events_no_update "
        "BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit events are immutable'); END"
    )
    connection.execute(
        "CREATE TRIGGER IF NOT EXISTS audit_events_no_delete "
        "BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit events are immutable'); END"
    )
    return connection


def _append_event(db_path: str | Path, event_type: str, payload: Mapping) -> dict:
    connection = _connect(db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        last = connection.execute(
            "SELECT event_hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = last["event_hash"] if last else GENESIS_HASH
        event = {
            "event_id": str(uuid.uuid4()),
            "occurred_at_utc": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            "event_type": event_type,
            "payload": dict(payload),
            "previous_hash": previous_hash,
        }
        event_hash = hashlib.sha256(_canonical(event).encode("utf-8")).hexdigest()
        connection.execute(
            """INSERT INTO audit_events
               (event_id, occurred_at_utc, event_type, payload_json, previous_hash, event_hash)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                event["event_id"], event["occurred_at_utc"], event_type,
                _canonical(dict(payload)), previous_hash, event_hash,
            ),
        )
        connection.commit()
        return {**event, "event_hash": event_hash}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def record_model_attempt(
    db_path: str | Path, *, discipline: str, model_result: Mapping, candidate_ids: Sequence[str]
) -> dict:
    if discipline not in {"batting", "bowling"}:
        raise ValueError("discipline must be batting or bowling")
    snapshot = dict(model_result)
    return _append_event(db_path, "MODEL_ATTEMPT", {
        "discipline": discipline,
        "candidate_ids": [str(value) for value in candidate_ids],
        "model_result": snapshot,
        "model_result_sha256": hashlib.sha256(_canonical(snapshot).encode("utf-8")).hexdigest(),
        "ranked_output_immutable": True,
    })


def record_owner_override(
    db_path: str | Path,
    *,
    overrides: Mapping[str, Sequence[str]],
    rationales: Mapping[str, str],
    model_results: Mapping[str, Mapping],
) -> dict:
    """Record one atomic override event; actor is explicitly not authenticated."""
    if set(overrides) != {"batting", "bowling"}:
        raise ValueError("override must contain batting and bowling selections")
    clean_overrides: dict[str, list[str]] = {}
    for discipline, values in overrides.items():
        ids = [str(value).strip() for value in values]
        if len(ids) != 10 or any(not value for value in ids) or len(set(ids)) != 10:
            raise ValueError(f"{discipline} override must contain exactly ten unique nonblank player IDs")
        if not str(rationales.get(discipline, "")).strip():
            raise ValueError(f"{discipline} override rationale is required")
        clean_overrides[discipline] = ids

    model_snapshots = {}
    for discipline in ("batting", "bowling"):
        result = dict(model_results.get(discipline, {}))
        model_snapshots[discipline] = {
            "status": result.get("status", "UNKNOWN"),
            "methodology_version": result.get("methodology_version"),
            "original_model_ranking": list(result.get("ranked", [])),
            "model_result_sha256": hashlib.sha256(_canonical(result).encode("utf-8")).hexdigest(),
        }

    return _append_event(db_path, "OWNER_OVERRIDE", {
        "actor_label": "UNAUTHENTICATED_APP_SESSION",
        "actor_identity_verified": False,
        "overrides": clean_overrides,
        "rationales": {key: str(rationales[key]).strip() for key in ("batting", "bowling")},
        "model_snapshots": model_snapshots,
        "model_output_modified": False,
        "data_mode": "SYNTHETIC_DEMO",
    })


def read_audit_events(db_path: str | Path) -> list[dict]:
    connection = _connect(db_path)
    try:
        rows = connection.execute(
            "SELECT * FROM audit_events ORDER BY sequence"
        ).fetchall()
        return [
            {
                "sequence": row["sequence"],
                "event_id": row["event_id"],
                "occurred_at_utc": row["occurred_at_utc"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "previous_hash": row["previous_hash"],
                "event_hash": row["event_hash"],
            }
            for row in rows
        ]
    finally:
        connection.close()


def verify_audit_chain(db_path: str | Path) -> dict:
    events = read_audit_events(db_path)
    previous_hash = GENESIS_HASH
    for index, event in enumerate(events, start=1):
        if event["previous_hash"] != previous_hash:
            return {"valid": False, "event_count": len(events), "failed_sequence": index}
        envelope = {
            "event_id": event["event_id"],
            "occurred_at_utc": event["occurred_at_utc"],
            "event_type": event["event_type"],
            "payload": event["payload"],
            "previous_hash": event["previous_hash"],
        }
        calculated = hashlib.sha256(_canonical(envelope).encode("utf-8")).hexdigest()
        if calculated != event["event_hash"]:
            return {"valid": False, "event_count": len(events), "failed_sequence": index}
        previous_hash = event["event_hash"]
    return {"valid": True, "event_count": len(events), "failed_sequence": None}
