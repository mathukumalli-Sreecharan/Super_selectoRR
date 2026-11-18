"""Synthetic and future-production pressure metric preparation.

This module implements deterministic delivery attribution and raw summaries.
Scenario and consistency estimands remain fail-closed when no approved rule exists.
"""

from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Mapping


def normalize_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def parse_int(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def delivery_attribution(row: Mapping) -> dict:
    """Apply the owner-confirmed delivery interpretation without inventing defaults."""
    runs = parse_int(row.get("runs"))
    extras1 = parse_int(row.get("extras1_runs"))
    extras2 = parse_int(row.get("extras_2_runs"))
    extras_type = str(row.get("extras_type") or "").strip()
    unknown_numbers = runs is None or extras1 is None and extras_type == "Overstep" or extras2 is None and extras_type == "Overstep"
    if unknown_numbers:
        return {
            "status": "NOT VALIDATED",
            "reason": "UNRESOLVED_NUMERIC_DELIVERY_FIELDS",
            "team_runs": None,
            "batter_runs": None,
            "bowler_runs": None,
            "batter_faced": None,
            "bowler_legal": None,
        }

    team_runs = runs
    lower = extras_type.lower()
    if lower == "overstep":
        batter_runs = extras2 or 0
        bowler_runs = (extras1 or 0) + batter_runs
        batter_faced = True
        bowler_legal = False
    elif lower == "wide":
        batter_runs = 0
        bowler_runs = runs
        batter_faced = False
        bowler_legal = False
    elif lower in {"other", "bye", "byes", "legbye", "legbyes"}:
        batter_runs = 0
        bowler_runs = 0 if lower in {"bye", "byes", "legbye", "legbyes"} else (extras2 or 0)
        batter_faced = False if lower in {"other", "wide"} else None
        if lower == "other":
            bowler_runs = runs
        bowler_legal = None if lower in {"bye", "byes", "legbye", "legbyes"} else False
    else:
        batter_runs = runs
        bowler_runs = runs
        batter_faced = True
        bowler_legal = True

    is_wicket = normalize_bool(row.get("is_wicket"))
    dismissal_id = parse_int(row.get("dismissal_type_id"))
    batter_dismissal = is_wicket is True
    bowler_credit = bool(is_wicket and dismissal_id in {1, 2, 3, 5})
    return {
        "status": "VALIDATED" if runs is not None and is_wicket is not None else "NOT VALIDATED",
        "reason": None if runs is not None and is_wicket is not None else "MISSING_RUN_OR_WICKET_FIELD",
        "team_runs": team_runs,
        "batter_runs": batter_runs,
        "bowler_runs": bowler_runs,
        "batter_faced": batter_faced,
        "bowler_legal": bowler_legal,
        "team_wicket": is_wicket is True,
        "batter_dismissal": batter_dismissal,
        "bowler_credit": bowler_credit,
    }


def reconstruct_delivery_states(deliveries: Iterable[Mapping]) -> list[dict]:
    """Reconstruct per-match/innings score and wicket state before each delivery."""
    ordered = []
    for row in deliveries:
        match_id = str(row.get("match_id", ""))
        innings_id = str(row.get("innings_id", row.get("innings", "")))
        sequence = parse_int(row.get("innings_ball_num", row.get("sequence")))
        ordered.append((match_id, innings_id, sequence if sequence is not None else 10**9, row))
    ordered.sort(key=lambda item: (item[0], item[1], item[2]))

    state = {}
    output = []
    for match_id, innings_id, sequence, row in ordered:
        key = (match_id, innings_id)
        before = state.setdefault(key, {"score": 0, "wickets": 0, "ball_index": 0})
        attr = delivery_attribution(row)
        pre_event = dict(before)
        if attr["status"] == "VALIDATED":
            before["score"] += attr["team_runs"]
            before["wickets"] += 1 if attr["team_wicket"] else 0
            before["ball_index"] += 1
        record = dict(row)
        record["_pre_event_state"] = pre_event
        record["_delivery_attribution"] = attr
        record["_source_row_ref"] = f"{match_id}:{innings_id}:{sequence}"
        output.append(record)
    return output


def batting_summary(deliveries: Iterable[Mapping]) -> list[dict]:
    totals = {}
    for row in reconstruct_delivery_states(deliveries):
        attr = row["_delivery_attribution"]
        player_id = str(row.get("striker_id", row.get("batter_id", "")))
        if not player_id:
            continue
        item = totals.setdefault(player_id, {
            "player_id": player_id, "player_name": str(row.get("striker_name", row.get("batter_name", player_id))),
            "batter_runs": 0, "balls_faced": 0, "dismissals": 0,
            "fours": 0, "sixes": 0, "team_wickets": 0,
            "validated_deliveries": 0, "exclusions": 0,
        })
        if attr["status"] != "VALIDATED":
            item["exclusions"] += 1
            continue
        item["validated_deliveries"] += 1
        if attr["batter_runs"] is not None:
            item["batter_runs"] += attr["batter_runs"]
        if attr["batter_faced"] is True:
            item["balls_faced"] += 1
        if attr["batter_dismissal"]:
            item["dismissals"] += 1
        if parse_int(row.get("is_four")) == 1:
            item["fours"] += 1
        if parse_int(row.get("is_six")) == 1:
            item["sixes"] += 1
    result = []
    for item in totals.values():
        faced = item["balls_faced"]
        item["strike_rate"] = round(item["batter_runs"] * 100 / faced, 2) if faced else None
        item["batting_average"] = round(item["batter_runs"] / item["dismissals"], 2) if item["dismissals"] else None
        item["boundary_percentage"] = round((item["fours"] + item["sixes"]) * 100 / faced, 2) if faced else None
        item["pressure_opportunities"] = 0
        item["pressure_scenario_status"] = "UNCLASSIFIED"
        item["evidence_status"] = "INSUFFICIENT EVIDENCE" if item["validated_deliveries"] == 0 else "VALIDATED COVERAGE"
        result.append(item)
    return sorted(result, key=lambda row: row["batter_runs"], reverse=True)


def bowling_summary(deliveries: Iterable[Mapping]) -> list[dict]:
    totals = {}
    for row in reconstruct_delivery_states(deliveries):
        attr = row["_delivery_attribution"]
        player_id = str(row.get("bowler_id", ""))
        if not player_id:
            continue
        item = totals.setdefault(player_id, {
            "player_id": player_id, "player_name": str(row.get("bowler_name", player_id)),
            "conceded_runs": 0, "legal_deliveries": 0, "bowler_wickets": 0,
            "dot_balls": 0, "boundaries_conceded": 0, "validated_deliveries": 0, "exclusions": 0,
        })
        if attr["status"] != "VALIDATED":
            item["exclusions"] += 1
            continue
        item["validated_deliveries"] += 1
        if attr["bowler_runs"] is not None:
            item["conceded_runs"] += attr["bowler_runs"]
        if attr["bowler_legal"] is True:
            item["legal_deliveries"] += 1
        if attr["bowler_credit"]:
            item["bowler_wickets"] += 1
        if attr["bowler_runs"] == 0:
            item["dot_balls"] += 1
        if parse_int(row.get("is_four")) == 1 or parse_int(row.get("is_six")) == 1:
            item["boundaries_conceded"] += 1
    result = []
    for item in totals.values():
        overs = item["legal_deliveries"] / 6
        item["economy"] = round(item["conceded_runs"] / overs, 2) if overs else None
        item["dot_percentage"] = round(item["dot_balls"] * 100 / item["validated_deliveries"], 2) if item["validated_deliveries"] else None
        item["bowling_average"] = round(item["conceded_runs"] / item["bowler_wickets"], 2) if item["bowler_wickets"] else None
        item["bowling_strike_rate"] = round(item["legal_deliveries"] / item["bowler_wickets"], 2) if item["bowler_wickets"] else None
        item["pressure_opportunities"] = 0
        item["recovery_evidence"] = "NOT ASSESSED"
        item["evidence_status"] = "INSUFFICIENT EVIDENCE" if item["validated_deliveries"] == 0 else "VALIDATED COVERAGE"
        result.append(item)
    return sorted(result, key=lambda row: row["conceded_runs"])


def scenario_status() -> dict:
    batting = {f"B{i}": "UNCLASSIFIED" for i in range(1, 11)}
    bowling = {f"W{i}": "UNCLASSIFIED" for i in range(1, 7)}
    batting.update({f"BAT-S{i:02}": "UNCLASSIFIED" for i in range(1, 10)})
    bowling.update({f"BWL-S{i:02}": "UNCLASSIFIED" for i in range(1, 10)})
    return {"batting": batting, "bowling": bowling}
