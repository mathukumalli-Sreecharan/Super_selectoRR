"""VAL-01 through VAL-07 orchestration; production entry is gated and unexecuted."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .authorization import authorize_stage2
from .source_adapter import iter_authorized_csv_rows
from .val01_delivery_sequence import validate_delivery_sequence
from .val02_runs_extras import validate_runs_and_extras
from .val03_wickets import validate_wickets
from .val04_batter_opportunity import validate_batter_opportunity
from .val05_bowler_opportunity import validate_bowler_opportunity
from .val06_identity import validate_player_identity
from .val07_target_state import validate_target_state


class SyntheticFixtureError(ValueError):
    pass


def run_synthetic_validation(
    deliveries: Sequence[Mapping[str, Any]],
    playing_eleven: Sequence[Mapping[str, Any]],
    target_evidence: Sequence[Mapping[str, Any]],
):
    """In-memory synthetic path only; callers must label fixture IDs SYN-* in tests."""
    if any(not str(row.get("fixture_id", "")).startswith("SYN-") for row in deliveries):
        raise SyntheticFixtureError("DELIVERY_FIXTURE_NOT_EXPLICITLY_SYNTHETIC")
    if any(not str(row.get("player_id", "")).startswith("SYN-") for row in playing_eleven):
        raise SyntheticFixtureError("PARTICIPATION_FIXTURE_NOT_EXPLICITLY_SYNTHETIC")
    if any(not str(row.get("fixture_id", "")).startswith("SYN-") for row in target_evidence):
        raise SyntheticFixtureError("TARGET_FIXTURE_NOT_EXPLICITLY_SYNTHETIC")
    return (
        validate_delivery_sequence(deliveries),
        validate_runs_and_extras(deliveries),
        validate_wickets(deliveries),
        validate_batter_opportunity(deliveries),
        validate_bowler_opportunity(deliveries),
        validate_player_identity(deliveries, playing_eleven),
        validate_target_state(target_evidence),
    )


def run_authorized_source_member(
    *, authorization_record: Mapping[str, Any] | None,
    archive_path: str, expected_archive_size: int, expected_archive_sha256: str,
    member_name: str, expected_member_size: int,
    expected_member_sha256: str,
):
    """Production preparation entry point. It fails at the current empty trust anchor."""
    authorize_stage2(authorization_record)
    return tuple(iter_authorized_csv_rows(
        authorization_record=authorization_record,
        archive_path=archive_path,
        expected_archive_size=expected_archive_size,
        expected_archive_sha256=expected_archive_sha256,
        member_name=member_name,
        expected_member_size=expected_member_size,
        expected_member_sha256=expected_member_sha256,
    ))
