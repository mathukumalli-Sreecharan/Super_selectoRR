"""VAL-06: direct stable-ID match/team/player participation reconciliation."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from .validation_common import result, row_exception


ACTORS = (
    ("striker_id", "striker_team_id"),
    ("non_striker_id", "non_striker_team_id"),
    ("bowler_id", "bowler_team_id"),
)


def validate_player_identity(
    deliveries: Sequence[Mapping[str, Any]], playing_eleven: Sequence[Mapping[str, Any]]
):
    vid = "VAL-06"
    issues = []
    counts = Counter(
        (row.get("match_id"), row.get("team_id"), row.get("player_id"))
        for row in playing_eleven
    )
    for key, count in counts.items():
        if any(value in (None, "") for value in key):
            issues.append(row_exception(vid, "PLAYING_ELEVEN_IDENTITY_MISSING", "UNRESOLVED", {"match_id": key[0], "team_id": key[1], "player_id": key[2]}))
        elif count > 1:
            issues.append(row_exception(vid, "DUPLICATE_PARTICIPATION_RECORD", "ERROR", {"match_id": key[0], "team_id": key[1], "player_id": key[2]}, expected_rule="Match/team/player key is unique unless formally defined otherwise."))
    participation = set(counts)
    for delivery in deliveries:
        for player_field, team_field in ACTORS:
            player, team, match = delivery.get(player_field), delivery.get(team_field), delivery.get("match_id")
            if player in (None, "") or team in (None, "") or match in (None, ""):
                issues.append(row_exception(vid, "DELIVERY_PARTICIPANT_LINK_MISSING", "UNRESOLVED", {**delivery, "player_id": player}, field_name=player_field, expected_rule="Direct match/team/player ID link is required; name similarity is not used."))
            elif (match, team, player) not in participation:
                issues.append(row_exception(vid, "DELIVERY_PARTICIPANT_UNMATCHED", "ERROR", {**delivery, "player_id": player}, field_name=player_field))
    return result(vid, deliveries, issues, metrics={"playing_eleven_rows": len(playing_eleven), "participation_keys": len(participation)})
