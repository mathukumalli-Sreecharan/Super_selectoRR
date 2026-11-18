"""Strict time-safe history eligibility; intentionally does not compute estimates."""
from datetime import datetime

from services.analysis_engines import _aware_datetime


def select_prior_records(records, *, player_id: str, competition: str, event_time: str, event_id: str | None = None, timestamp_field: str = "event_time"):
    if not player_id or not competition:
        raise ValueError("Player and competition identity are required for a baseline population.")
    cutoff = _aware_datetime(event_time)
    selected = []
    for row in records:
        if row.get("player_id") != player_id or row.get("competition") != competition:
            continue
        if event_id is not None and row.get("event_id") == event_id:
            continue
        stamp = row.get(timestamp_field)
        if not stamp:
            raise ValueError("Missing historical timestamp; baseline eligibility is not established.")
        timestamp = _aware_datetime(str(stamp))
        if timestamp < cutoff:
            selected.append(row)
    selected.sort(key=lambda row: (_aware_datetime(str(row[timestamp_field])), str(row.get("event_id", ""))))
    return selected


def baseline_status(history: list[dict], *, source_semantics_validated: bool, metric_definition_approved: bool) -> str:
    if not source_semantics_validated or not metric_definition_approved or not history:
        return "NOT READY"
    return "ELIGIBLE HISTORY ONLY — NO ESTIMATE COMPUTED"
