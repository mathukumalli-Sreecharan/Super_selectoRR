"""Explicit opportunity records; never infer exposure from player appearance."""
from collections import Counter

from models.analytics import OpportunityRecord


def parse_opportunity(row: dict, *, event_index: dict[str, dict] | None = None) -> OpportunityRecord:
    required = ("opportunity_id", "player_id", "event_id", "opportunity_status")
    missing = [key for key in required if not row.get(key)]
    if missing:
        raise ValueError("Opportunity lacks explicit evidence fields: " + ", ".join(missing))
    event = (event_index or {}).get(str(row["event_id"]), {})
    match_id = row.get("match_id") or event.get("match_id")
    if not match_id:
        raise ValueError("Opportunity lacks explicit match identity or a resolvable event-to-match reference")
    return OpportunityRecord(
        opportunity_id=str(row["opportunity_id"]), player_id=str(row["player_id"]),
        match_id=str(match_id), innings_id=str(row.get("innings_id") or event.get("innings_id") or "UNRESOLVED"),
        event_id=str(row["event_id"]), scenario_id=row.get("scenario_id"),
        status=str(row["opportunity_status"]), opportunity_type=str(row.get("opportunity_type", "UNRESOLVED")),
        source_refs=tuple(row.get("source_record_refs", ())),
        exclusion_reason=row.get("exclusion_reason"),
    )


def validate_opportunities(rows: list[dict], *, event_records: list[dict] | None = None) -> tuple[OpportunityRecord, ...]:
    event_index = {str(event.get("event_id")): event for event in (event_records or []) if event.get("event_id")}
    parsed = tuple(parse_opportunity(row, event_index=event_index) for row in rows)
    ids = [record.opportunity_id for record in parsed]
    duplicates = [key for key, count in Counter(ids).items() if not key or count > 1]
    if duplicates:
        raise ValueError(f"Missing/duplicate opportunity IDs: {duplicates}")
    return parsed


def eligible_fixture_opportunities(rows: list[dict], *, discipline: str, event_records: list[dict] | None = None) -> tuple[OpportunityRecord, ...]:
    """Read only explicitly labelled synthetic fixture opportunities."""
    if discipline not in {"BAT", "BWL"}:
        raise ValueError("discipline must be BAT or BWL")
    parsed = validate_opportunities(rows, event_records=event_records)
    expected_type = "BATTER_DELIVERY" if discipline == "BAT" else "BOWLER_DELIVERY"
    return tuple(op for op in parsed if op.status == "ELIGIBLE (SYNTHETIC)" and op.opportunity_id.startswith("SYN-") and op.opportunity_type == expected_type)
