"""VAL-05: bowler delivery, legal-ball and conceded-run inputs."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .validation_common import integer_value, result, row_exception


def validate_bowler_opportunity(rows: Sequence[Mapping[str, Any]]):
    vid = "VAL-05"
    issues = []
    legal_balls = conceded = 0
    balls_complete = runs_complete = True
    for row in rows:
        if row.get("bowler_id") in (None, ""):
            issues.append(row_exception(vid, "BOWLER_ID_MISSING", "UNRESOLVED", row, field_name="bowler_id"))
            balls_complete = runs_complete = False
            continue
        category = row.get("extras_type")
        if category in (None, "normal"):
            legal_balls += 1
        elif category in {"wide", "Overstep", "Other"}:
            pass
        elif category in {"byes", "legbyes"}:
            status = row.get("underlying_legal")
            if type(status) is bool:
                legal_balls += int(status)
            else:
                issues.append(row_exception(vid, "UNDERLYING_LEGALITY_UNAVAILABLE", "UNRESOLVED", row, field_name="extras_type"))
                balls_complete = False
        else:
            issues.append(row_exception(vid, "BOWLER_LEGALITY_UNMAPPED", "UNRESOLVED", row, field_name="extras_type"))
            balls_complete = False
        runs = integer_value(row.get("runs"))
        if runs is None or runs < 0:
            issues.append(row_exception(vid, "BOWLER_RUN_INPUT_INVALID", "UNRESOLVED", row, field_name="runs"))
            runs_complete = False
        elif category in (None, "normal", "Overstep", "wide", "Other"):
            conceded += runs
        elif category in {"byes", "legbyes"}:
            pass
    return result(vid, rows, issues, metrics={"bowler_legal_deliveries": legal_balls if balls_complete else None, "bowler_conceded_runs": conceded if runs_complete else None})
