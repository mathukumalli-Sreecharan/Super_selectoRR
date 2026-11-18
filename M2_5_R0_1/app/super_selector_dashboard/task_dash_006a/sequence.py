"""Deterministic event ordering and strictly prior-only time selection."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .reporting import ValidationFinding, ValidationReport


def _aware(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def validate_delivery_order(
    rows: Sequence[Mapping[str, Any]], *, timestamp_semantics: str = "UNVERIFIED", evidence_ref: str = "SYNTHETIC:sequence_fixture"
) -> ValidationReport:
    findings: list[ValidationFinding] = []
    def add(ref: str, status: str, code: str, disposition: str) -> None:
        findings.append(ValidationFinding("DELIVERY_SEQUENCE", ref, status, code, evidence_ref, "", disposition))
    required = ("match_id", "innings_id", "delivery_id", "delivery_seq")
    keys: set[tuple[str, str, int]] = set()
    last_seq_by_innings: dict[tuple[str, str], int] = {}
    times: dict[tuple[str, str], list[tuple[int, datetime]]] = {}
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        missing = [field for field in required if row.get(field) in (None, "")]
        if missing:
            add(f"row:{index + 1}", "FAIL", "MISSING_DELIVERY_IDENTITY", "Quarantine record; do not invent a key or sequence.")
            continue
        seq = row["delivery_seq"]
        if type(seq) is not int or seq < 1:
            add(str(row["delivery_id"]), "FAIL", "INVALID_DELIVERY_SEQUENCE", "Resolve deterministic event order before state reconstruction.")
            continue
        key = (str(row["match_id"]), str(row["innings_id"]), seq)
        group = (key[0], key[1])
        if group in last_seq_by_innings and seq <= last_seq_by_innings[group]:
            add(str(row["delivery_id"]), "FAIL", "NON_MONOTONIC_DELIVERY_ORDER", "Restore unique increasing source order; do not reorder events silently.")
        last_seq_by_innings[group] = seq
        if key in keys:
            add(str(row["delivery_id"]), "FAIL", "AMBIGUOUS_DELIVERY_ORDER", "Quarantine duplicate sequence; do not choose an arbitrary event order.")
        keys.add(key)
        did = str(row["delivery_id"])
        if did in seen_ids:
            add(did, "FAIL", "DUPLICATE_DELIVERY_ID", "Resolve duplicate event identity before accumulation.")
        seen_ids.add(did)
        if timestamp_semantics == "VERIFIED":
            parsed = _aware(row.get("event_time"))
            if parsed is None:
                add(did, "FAIL", "INVALID_OR_MISSING_EVENT_TIMESTAMP", "Quarantine event-time-dependent state; do not infer a timestamp.")
            else:
                times.setdefault((key[0], key[1]), []).append((seq, parsed))
    for group, pairs in times.items():
        ordered = sorted(pairs)
        if any(current[1] <= prior[1] for prior, current in zip(ordered, ordered[1:])):
            add("/".join(group), "FAIL", "TIMESTAMP_SEQUENCE_CONFLICT", "Resolve event-time/sequence conflict with the steward; do not reorder silently.")
    if timestamp_semantics != "VERIFIED":
        add("timestamp_semantics", "NOT_VERIFIABLE", "EVENT_TIME_SEMANTICS_UNVERIFIED", "Sequence checks do not establish timestamp meaning; exclude time-dependent features.")
    status = "FAIL" if any(x.status == "FAIL" for x in findings) else "PASS"
    return ValidationReport("DELIVERY_SEQUENCE", status, tuple(findings))


def strictly_prior_events(
    rows: Sequence[Mapping[str, Any]], *, evaluated_at: str, timestamp_semantics: str, evidence_ref: str = "SYNTHETIC:prior_only_fixture"
) -> tuple[tuple[Mapping[str, Any], ...], ValidationFinding | None]:
    if timestamp_semantics != "VERIFIED":
        return (), ValidationFinding("TEMPORAL_SCOPE", "history", "NOT_VERIFIABLE", "EVENT_TIME_SEMANTICS_UNVERIFIED", evidence_ref, "", "Do not construct prior-only context.")
    cutoff = _aware(evaluated_at)
    if cutoff is None:
        return (), ValidationFinding("TEMPORAL_SCOPE", "evaluation", "FAIL", "INVALID_EVALUATION_CUTOFF", evidence_ref, "", "Reject time-dependent analysis; provide an aware timestamp.")
    prior = []
    for index, row in enumerate(rows):
        stamp = _aware(row.get("event_time"))
        if stamp is None:
            return (), ValidationFinding("TEMPORAL_SCOPE", f"history:{index + 1}", "FAIL", "INVALID_HISTORY_TIMESTAMP", evidence_ref, "", "Reject history selection; do not coerce or impute timestamps.")
        if stamp < cutoff:
            prior.append(row)
    return tuple(prior), None
