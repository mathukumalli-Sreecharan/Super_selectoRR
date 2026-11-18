"""VAL-03: explicit team wicket and bowler-credit wicket accounting."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .validation_common import integer_value, result, row_exception


BOWLER_CREDIT = {1: 1, 2: 1, 3: 1, 4: 0, 5: 1}


def validate_wickets(rows: Sequence[Mapping[str, Any]]):
    vid = "VAL-03"
    issues = []
    team_wickets = 0
    bowler_wickets = 0
    bowler_complete = True
    for row in rows:
        flag = row.get("is_wicket")
        kind = integer_value(row.get("dismissal_type_id"))
        if type(flag) is not bool:
            issues.append(row_exception(vid, "IS_WICKET_UNVERIFIED", "UNRESOLVED", row, field_name="is_wicket"))
            bowler_complete = False
            continue
        if not flag:
            if kind not in (None, ""):
                issues.append(row_exception(vid, "DISMISSAL_WITHOUT_WICKET_FLAG", "ERROR", row, field_name="dismissal_type_id"))
            continue
        team_wickets += 1
        if type(kind) is not int or kind not in BOWLER_CREDIT:
            issues.append(row_exception(vid, "DISMISSAL_TYPE_UNMAPPED", "UNRESOLVED", row, field_name="dismissal_type_id"))
            bowler_complete = False
        else:
            bowler_wickets += BOWLER_CREDIT[kind]
    return result(vid, rows, issues, metrics={"team_wickets": team_wickets, "bowler_wickets": bowler_wickets if bowler_complete else None})
