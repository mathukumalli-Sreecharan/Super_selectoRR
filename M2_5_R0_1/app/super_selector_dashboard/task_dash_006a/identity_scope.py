"""Exact-key identity, participation and competition checks for normalized rows."""

from __future__ import annotations

from typing import Mapping, Sequence

from .reporting import ValidationFinding, ValidationReport


def validate_identity_and_scope(
    *,
    deliveries: Sequence[Mapping[str, str]],
    matches: Sequence[Mapping[str, str]],
    competitions: Sequence[Mapping[str, str]],
    teams: Sequence[Mapping[str, str]],
    participation: Sequence[Mapping[str, str]],
    required_seasons: frozenset[str] = frozenset({"2022", "2023", "2024", "2025", "2026"}),
    evidence_ref: str = "SYNTHETIC:identity_scope_fixture",
) -> ValidationReport:
    findings: list[ValidationFinding] = []
    def add(ref: str, code: str, disposition: str) -> None:
        findings.append(ValidationFinding("IDENTITY_SCOPE", ref, "FAIL", code, evidence_ref, "", disposition))
    match_ids = [r.get("match_id", "") for r in matches]
    comp_ids = [r.get("comp_id", "") for r in competitions]
    if "" in match_ids:
        add("matches", "MISSING_MATCH_ID", "Quarantine match and dependent rows.")
    if len(match_ids) != len(set(match_ids)):
        add("matches", "DUPLICATE_MATCH_ID", "Resolve exact-key conflict with the steward; do not select a row silently.")
    if "" in comp_ids or len(comp_ids) != len(set(comp_ids)):
        add("competitions", "MISSING_OR_DUPLICATE_COMPETITION_ID", "Resolve competition identity by authoritative identifier.")
    comp_map = {row.get("comp_id", ""): row for row in competitions if row.get("comp_id")}
    match_map = {row.get("match_id", ""): row for row in matches if row.get("match_id")}
    team_keys = [(row.get("comp_id", ""), row.get("team_id", "")) for row in teams]
    if any(not all(key) for key in team_keys) or len(team_keys) != len(set(team_keys)):
        add("teams", "MISSING_OR_DUPLICATE_TEAM_IDENTITY", "Resolve competition-scoped team IDs using the authoritative identifier contract.")
    team_key_set = set(team_keys)
    for match in matches:
        comp_id = match.get("comp_id", "")
        for field in ("home_team_id", "away_team_id"):
            team_id = match.get(field, "")
            if not team_id or (comp_id, team_id) not in team_key_set:
                add(match.get("match_id", "matches"), "UNMAPPED_MATCH_TEAM_ID", "Resolve exact competition-scoped team identity; do not use team names as fallback.")
    participant_keys = set()
    seen_participation_keys = set()
    for row in participation:
        key = (row.get("match_id", ""), row.get("team_id", ""), row.get("player_id", ""))
        if not all(key):
            add("participation", "MISSING_PARTICIPATION_IDENTITY", "Retain as unresolved; do not infer participation from names or event presence.")
        if key in seen_participation_keys:
            add("participation", "DUPLICATE_PARTICIPATION_KEY", "Resolve duplicate participation rows with the steward; do not select a record silently.")
        seen_participation_keys.add(key)
        if type(row.get("participated")) is not bool:
            add("participation", "INVALID_NORMALIZED_PARTICIPATION_FLAG", "Resolve source participation semantics and provide an explicit normalized boolean; do not coerce flags.")
        elif row["participated"]:
            participant_keys.add(key)
    for match in matches:
        comp = comp_map.get(match.get("comp_id", ""))
        if comp is None:
            add(match.get("match_id", "matches"), "UNMAPPED_COMPETITION_ID", "Quarantine match from competition-specific analysis.")
            continue
        if comp.get("competition_code") != "IPL" or comp.get("season") not in required_seasons:
            add(match.get("match_id", "matches"), "OUT_OF_SCOPE_COMPETITION", "Exclude from IPL 2022–2026 population; preserve separate source evidence.")
    delivery_ids = [row.get("delivery_id", "") for row in deliveries]
    if "" in delivery_ids:
        add("deliveries", "MISSING_DELIVERY_ID", "Do not synthesize an identity without an approved unique-grain rule.")
    if len(delivery_ids) != len(set(delivery_ids)):
        add("deliveries", "DUPLICATE_DELIVERY_ID", "Quarantine conflicting event identity; retain all locators.")
    for row in deliveries:
        match_id = row.get("match_id", "")
        match = match_map.get(match_id)
        if match is None:
            add(row.get("delivery_id", "delivery"), "UNMAPPED_MATCH_ID", "Quarantine delivery; do not infer its match.")
            continue
        if not row.get("innings_id"):
            add(row.get("delivery_id", "delivery"), "MISSING_INNINGS_ID", "Do not reconstruct state until innings identity is resolved.")
        for team_field in ("batting_team_id", "bowling_team_id"):
            if (match.get("comp_id", ""), row.get(team_field, "")) not in team_key_set:
                add(row.get("delivery_id", "delivery"), "UNMAPPED_DELIVERY_TEAM_ID", "Resolve competition-scoped team identity before state reconstruction.")
        for field, team_field in (("striker_id", "batting_team_id"), ("non_striker_id", "batting_team_id"), ("bowler_id", "bowling_team_id")):
            player, team = row.get(field, ""), row.get(team_field, "")
            if not player or not team:
                add(row.get("delivery_id", "delivery"), "MISSING_ACTOR_OR_TEAM_ID", "Retain unresolved actor identity; never name-match.")
            elif (match_id, team, player) not in participant_keys:
                add(row.get("delivery_id", "delivery"), "UNMAPPED_PARTICIPATION", "Resolve participation/substitute semantics with steward; do not infer from names.")
    status = "PASS" if not findings else "FAIL"
    return ValidationReport("IDENTITY_SCOPE", status, tuple(findings))
