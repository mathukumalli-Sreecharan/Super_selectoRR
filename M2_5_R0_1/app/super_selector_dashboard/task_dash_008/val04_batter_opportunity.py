"""VAL-04: batter participation and balls-faced eligibility."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .validation_common import result, row_exception


def validate_batter_opportunity(rows: Sequence[Mapping[str, Any]]):
    vid = "VAL-04"
    issues = []
    balls = 0
    complete = True
    for row in rows:
        if row.get("striker_id") in (None, ""):
            issues.append(row_exception(vid, "STRIKER_ID_MISSING", "UNRESOLVED", row, field_name="striker_id"))
            complete = False
            continue
        category = row.get("extras_type")
        if category in (None, "normal", "Overstep"):
            balls += 1
        elif category in {"wide", "Other"}:
            continue
        elif category in {"byes", "legbyes"}:
            legal = row.get("underlying_legal")
            if type(legal) is bool:
                balls += int(legal)
            else:
                issues.append(row_exception(vid, "BYE_BALL_FACED_STATUS_UNAVAILABLE", "UNRESOLVED", row, field_name="extras_type"))
                complete = False
        else:
            issues.append(row_exception(vid, "BATTER_BALL_CATEGORY_UNMAPPED", "UNRESOLVED", row, field_name="extras_type"))
            complete = False
    return result(vid, rows, issues, metrics={"batter_balls_faced": balls if complete else None})
