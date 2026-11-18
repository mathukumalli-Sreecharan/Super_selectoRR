"""Research-layer engine contracts for TASK-DASH-002 v0.1.5."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping, Any

from models.analytics import AnalysisResult, DimensionAssessment


class Stage2AuthorizationRequired(RuntimeError):
    pass


AnalysisDisposition = AnalysisResult


def not_ready(discipline: str, *reasons: str, status: str = "NOT READY") -> AnalysisResult:
    return AnalysisResult(status=status, discipline=discipline, reasons=tuple(reasons))


def batting_analysis(_records) -> AnalysisDisposition:
    from services.batting_engine import analyze_batting
    return analyze_batting(_records)


def bowling_analysis(_records) -> AnalysisDisposition:
    from services.bowling_engine import analyze_bowling
    return analyze_bowling(_records)


def select_top_ten(_candidates, *, discipline: str) -> AnalysisDisposition:
    from services.ranking_engine import select_candidates
    return select_candidates(_candidates, discipline=discipline, mode="SYNTHETIC")


def compare_players(_left, _right) -> AnalysisDisposition:
    from services.ranking_engine import compare_candidates
    return compare_candidates(_left, _right)


def prior_only_history(records, *, player_id: str, event_time: str, timestamp_field: str = "event_time", competition: str | None = None, event_id: str | None = None):
    """Select same-player, same-competition records strictly before event time.

    This selects eligible history only; it does not aggregate a baseline or
    choose a lookback window/estimator. Missing or conflicting competition/time
    metadata fails closed. Equal timestamps are excluded.
    """
    if not event_time:
        raise ValueError("An event-time cutoff is required; future-safe history cannot be inferred.")
    cutoff = _aware_datetime(event_time)
    selected = []
    for record in records:
        if record.get("player_id") != player_id or (event_id is not None and record.get("event_id") == event_id):
            continue
        if competition is not None and record.get("competition") != competition:
            continue
        stamp = record.get(timestamp_field)
        if stamp is None:
            raise ValueError("A candidate historical record has no timestamp; prior-only eligibility cannot be established.")
        if _aware_datetime(str(stamp)) < cutoff:
            selected.append(record)
    selected.sort(key=lambda row: (_aware_datetime(str(row[timestamp_field])), str(row.get("event_id", ""))))
    return selected


def _aware_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid event timestamp: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Naive event timestamps are rejected; timezone-aware cutoffs are required.")
    return parsed.astimezone(timezone.utc)


def effectiveness(*, observed: Any = None, expected: Any = None, readiness_status: str = "NOT READY") -> DimensionAssessment:
    """No subtraction/ratio is selected until an estimand and scale are approved."""
    return DimensionAssessment("effectiveness", "NOT READY", None, "Requires an approved outcome, personal expectation, scale and metric readiness.")


def consistency(*, observations: Iterable[Any] = (), readiness_status: str = "NOT READY") -> DimensionAssessment:
    return DimensionAssessment("consistency", "NOT READY", None, "Conceptual only; estimand, comparable opportunities, noise and dependence method are unresolved.")


def reliability(*, evidence: Mapping[str, Any] | None = None) -> DimensionAssessment:
    return DimensionAssessment("reliability", "NOT READY", None, "Report source validity, coverage, sample and uncertainty separately; no validated composite or confidence label is approved.")
