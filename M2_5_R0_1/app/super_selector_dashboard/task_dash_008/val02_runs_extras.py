"""VAL-02: delivery, batter, team and bowler run attribution."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .validation_common import integer_value, nonnegative_int, result, row_exception


def validate_runs_and_extras(rows: Sequence[Mapping[str, Any]]):
    vid = "VAL-02"
    issues = []
    team_total = 0
    batter_total = 0
    bowler_total = 0
    team_complete = batter_complete = bowler_complete = True
    for row in rows:
        runs_raw = row.get("runs")
        runs = integer_value(runs_raw)
        if not nonnegative_int(runs):
            issues.append(row_exception(vid, "DELIVERY_RUNS_INVALID_OR_UNVERIFIED", "ERROR", row, field_name="runs", expected_rule="Non-negative integer; count once for team."))
            team_complete = False
            batter_complete = bowler_complete = False
            continue
        team_total += runs
        category = row.get("extras_type")
        b_runs: int | None = None
        w_runs: int | None = None
        if category in (None, "normal"):
            b_runs = w_runs = runs
        elif category == "Overstep":
            penalty = integer_value(row.get("extras1_runs"))
            batter_component = integer_value(row.get("extras_2_runs"))
            if not nonnegative_int(penalty) or not nonnegative_int(batter_component):
                issues.append(row_exception(vid, "NO_BALL_COMPONENT_INVALID_OR_MISSING", "UNRESOLVED", row, expected_rule="Owner-confirmed penalty + batter component must be present numeric non-negative values."))
            elif penalty + batter_component != runs:
                issues.append(row_exception(vid, "NO_BALL_COMPONENTS_DO_NOT_RECONCILE", "ERROR", row, expected_rule="extras1_runs + extras_2_runs == runs."))
            else:
                b_runs, w_runs = batter_component, runs
        elif category in {"wide", "Other"}:
            b_runs, w_runs = 0, runs
        elif category in {"byes", "legbyes"}:
            b_runs, w_runs = 0, 0
        else:
            issues.append(row_exception(vid, "EXTRAS_CATEGORY_UNMAPPED", "UNRESOLVED", row, field_name="extras_type"))
        if b_runs is None:
            batter_complete = False
        else:
            batter_total += b_runs
        if w_runs is None:
            bowler_complete = False
        else:
            bowler_total += w_runs
    metrics = {
        "team_runs": team_total if team_complete else None,
        "batter_runs": batter_total if batter_complete else None,
        "bowler_conceded_runs": bowler_total if bowler_complete else None,
    }
    return result(vid, rows, issues, metrics=metrics)
