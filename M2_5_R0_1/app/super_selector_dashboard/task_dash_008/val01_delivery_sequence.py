"""VAL-01: deterministic delivery ordering and legal-ball hypothesis checks."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

from .validation_common import ValidationException, integer_value, positive_int, result, row_exception


def _legal(row: Mapping[str, Any]) -> int | None:
    category = row.get("extras_type")
    if category in (None, "normal"):
        return 1
    if category in {"wide", "Overstep", "Other"}:
        return 0
    if category in {"byes", "legbyes"}:
        value = row.get("underlying_legal")
        return int(value) if type(value) is bool else None
    return None


def validate_delivery_sequence(rows: Sequence[Mapping[str, Any]]) :
    vid = "VAL-01"
    issues: list[ValidationException] = []
    groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    group_positions: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    seen: set[tuple[str, str, int]] = set()
    innings_positions: dict[tuple[str, str], list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
    for position, row in enumerate(rows):
        match, innings, over = (row.get(k) for k in ("match_id", "innings_id", "overid"))
        if any(value in (None, "") for value in (match, innings, over)):
            issues.append(row_exception(vid, "SEQUENCE_IDENTITY_MISSING", "ERROR", row, expected_rule="Match, innings and over identities are required."))
            continue
        ball = integer_value(row.get("innings_ball_num"))
        if not positive_int(ball):
            issues.append(row_exception(vid, "INNINGS_BALL_ORDER_UNVERIFIED", "UNRESOLVED", row, field_name="innings_ball_num", expected_rule="Positive unique numeric sequence required."))
        else:
            key = (str(match), str(innings), ball)
            if key in seen:
                issues.append(row_exception(vid, "DUPLICATE_DELIVERY_SEQUENCE", "ERROR", row, field_name="innings_ball_num"))
            seen.add(key)
            innings_positions[(str(match), str(innings))].append((position, row))
        over_ball = integer_value(row.get("over_ball_num"))
        if not positive_int(over_ball):
            issues.append(row_exception(vid, "OVER_BALL_NUMBER_UNVERIFIED", "UNRESOLVED", row, field_name="over_ball_num"))
        group_key = (str(match), str(innings), str(over))
        groups[group_key].append(row)
        group_positions[group_key].append(position)
    # Verify the source's observed order is deterministic and each over is contiguous.
    closed_groups: set[tuple[str, str, str]] = set()
    previous_innings_ball: dict[tuple[str, str], int] = {}
    active_match: str | None = None
    active_innings: str | None = None
    active_over: str | None = None
    closed_matches: set[str] = set()
    closed_innings: set[tuple[str, str]] = set()
    previous_over_number: int | None = None
    for row in rows:
        match, innings, over = (str(row.get(k)) for k in ("match_id", "innings_id", "overid"))
        innings_key = (match, innings)
        current_group = (match, innings, over)
        if match != active_match:
            if active_match is not None:
                closed_matches.add(active_match)
                if active_innings is not None:
                    closed_innings.add((active_match, active_innings))
                if active_over is not None and active_innings is not None:
                    closed_groups.add((active_match, active_innings, active_over))
            if match in closed_matches:
                issues.append(row_exception(vid, "MATCH_GROUP_REAPPEARS_AFTER_TRANSITION", "ERROR", row, field_name="match_id"))
            active_match, active_innings, active_over = match, None, None
            previous_over_number = None
        if innings != active_innings:
            if active_innings is not None:
                closed_innings.add((match, active_innings))
                if active_over is not None:
                    closed_groups.add((match, active_innings, active_over))
            if (match, innings) in closed_innings:
                issues.append(row_exception(vid, "INNINGS_GROUP_REAPPEARS_AFTER_TRANSITION", "ERROR", row, field_name="innings_id"))
            active_innings, active_over = innings, None
            previous_over_number = None
        if over != active_over:
            if active_over is not None:
                closed_groups.add((match, innings, active_over))
            current_over_number = integer_value(row.get("overid"))
            if current_group in closed_groups:
                issues.append(row_exception(vid, "OVER_GROUP_REAPPEARS_AFTER_TRANSITION", "ERROR", row, field_name="overid"))
            if active_over is not None:
                if current_over_number is None or previous_over_number is None:
                    issues.append(row_exception(vid, "OVER_ID_ORDER_UNVERIFIED", "UNRESOLVED", row, field_name="overid"))
                elif current_over_number <= previous_over_number:
                    issues.append(row_exception(vid, "OVER_ID_NOT_INCREASING", "ERROR", row, field_name="overid"))
                elif current_over_number > previous_over_number + 1:
                    issues.append(row_exception(vid, "OVER_ID_SEQUENCE_GAP", "UNRESOLVED", row, field_name="overid"))
            active_over = over
            previous_over_number = current_over_number
        seq = integer_value(row.get("innings_ball_num"))
        if seq is not None:
            prior_seq = previous_innings_ball.get(innings_key)
            if prior_seq is not None and seq != prior_seq + 1:
                code = "INNINGS_SEQUENCE_NOT_MONOTONIC" if seq <= prior_seq else "INNINGS_SEQUENCE_GAP"
                severity = "ERROR" if seq <= prior_seq else "UNRESOLVED"
                issues.append(row_exception(vid, code, severity, row, field_name="innings_ball_num"))
            previous_innings_ball[innings_key] = seq
    for key, group in groups.items():
        valid = [r for r in group if positive_int(r.get("over_ball_num"))]
        if valid:
            numbers = [integer_value(r["over_ball_num"]) for r in valid]
            if numbers != list(range(1, len(numbers) + 1)):
                issues.append(row_exception(vid, "OVER_BALL_SEQUENCE_GAP_OR_ORDER", "ERROR", valid[-1], field_name="over_ball_num"))
            legal = [_legal(row) for row in valid]
            if any(value is None for value in legal):
                issues.append(row_exception(vid, "LEGAL_BALL_CATEGORY_UNRESOLVED", "UNRESOLVED", valid[-1], field_name="extras_type"))
            elif numbers[-1] == 6 and (len(valid) != 6 or sum(legal) != 6):
                issues.append(row_exception(vid, "SIX_BALL_ENDING_HYPOTHESIS_CONTRADICTED", "ERROR", valid[-1], expected_rule="Synthetic working hypothesis: six legal deliveries at over_ball_num 6."))
            elif numbers[-1] > 6 and sum(legal) > 6:
                issues.append(row_exception(vid, "OVER_ABOVE_SIX_HAS_MORE_THAN_SIX_LEGAL", "ERROR", valid[-1], expected_rule="Identify extra wide/no-ball events; do not exceed six legal deliveries."))
            elif numbers[-1] > 6 and sum(legal) < 6:
                last_position = group_positions[key][-1]
                following = rows[last_position + 1] if last_position + 1 < len(rows) else None
                final_transition = (
                    following is not None
                    and following.get("match_id") == valid[-1].get("match_id")
                    and following.get("innings_id") != valid[-1].get("innings_id")
                )
                if final_transition:
                    issues.append(row_exception(vid, "INCOMPLETE_FINAL_OVER_RETAINED", "LIMITATION", valid[-1], expected_rule="Observed same-match innings transition; retain observed legal count."))
                else:
                    issues.append(row_exception(vid, "OVER_ABOVE_SIX_LEGAL_COUNT_NOT_RECONCILED", "UNRESOLVED", valid[-1], expected_rule="Six legal deliveries expected after classifying extra deliveries."))
    ordered = sorted(
        (r for r in rows if positive_int(r.get("innings_ball_num"))),
        key=lambda r: (str(r.get("match_id")), str(r.get("innings_id")), integer_value(r["innings_ball_num"])),
    )
    for left, right in zip(ordered, ordered[1:]):
        if left.get("match_id") == right.get("match_id") and left.get("innings_id") != right.get("innings_id"):
            # A short ending is retained as a limitation; no forced six-ball completion.
            over_rows = [r for r in rows if r.get("match_id") == left.get("match_id") and r.get("innings_id") == left.get("innings_id") and r.get("overid") == left.get("overid")]
            legal = [_legal(r) for r in over_rows]
            end_number = integer_value(left.get("over_ball_num"))
            if (
                legal and all(value is not None for value in legal)
                and sum(legal) < 6
                and end_number is not None and end_number <= 6
            ):
                issues.append(row_exception(vid, "INCOMPLETE_FINAL_OVER_RETAINED", "LIMITATION", left, expected_rule="Same-match innings transition; retain observed legal count."))
    return result(vid, rows, issues, metrics={"over_groups": len(groups)}, records_passed=max(0, len(rows) - sum(i.severity == "ERROR" for i in issues)))
