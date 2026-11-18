"""Fail-closed automatic ranking contract.

This module screens the supplied candidate evidence but deliberately does not
assign ranks until an approved, versioned methodology is available.  Screening
counts are not final player eligibility or ranking decisions.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping

RANKING_METHODOLOGY_VERSION = "TASK-DASH-011-AUTO-RANK-CONTRACT-v0.2-UNAPPROVED"
SUPPORTED_DISCIPLINES = {"batting", "bowling"}


def _empty_result(status: str, reason: str, *, discipline: str, counts: dict | None = None) -> dict:
    return {
        "status": status,
        "discipline": discipline,
        "methodology_version": RANKING_METHODOLOGY_VERSION,
        "ranked": [],
        "next_candidates": [],
        "preliminary_evidence_screen_count": 0,
        "input_candidate_count": 0,
        "excluded_reason_counts": {},
        "reason": reason,
    } | (counts or {})


def automatic_rank(candidates: Iterable[Mapping], *, discipline: str) -> dict:
    """Return a non-ranking status until approved methodology is bound.

    A preliminary screen requires a stable player ID, positive integer pressure
    opportunities, exact ``VALIDATED`` evidence status, and exact ``CLASSIFIED``
    scenario status.  These checks only establish that a row can be considered
    for later methodology review; they do not establish final eligibility.
    """
    if discipline not in SUPPORTED_DISCIPLINES:
        return _empty_result(
            "NOT VALIDATED", "Unknown discipline.", discipline=str(discipline)
        )

    rows = [dict(row) for row in candidates]
    if not rows:
        return _empty_result(
            "NO-RANK", "No candidate evidence rows were supplied.", discipline=discipline
        )

    excluded = Counter()
    seen_ids: set[str] = set()
    preliminary_pool: list[dict] = []

    for row in rows:
        player_id = str(row.get("player_id", "")).strip()
        if not player_id:
            excluded["MISSING_PLAYER_ID"] += 1
            continue
        if player_id in seen_ids:
            excluded["DUPLICATE_PLAYER_ID"] += 1
            continue
        seen_ids.add(player_id)

        opportunities = row.get("pressure_opportunities")
        if isinstance(opportunities, bool) or not isinstance(opportunities, int) or opportunities <= 0:
            excluded["NO_VALID_PRESSURE_OPPORTUNITIES"] += 1
            continue

        if str(row.get("evidence_status", "")).strip().upper() != "VALIDATED":
            excluded["PRESSURE_EVIDENCE_NOT_VALIDATED"] += 1
            continue

        scenario_status = str(
            row.get("pressure_scenario_status", row.get("scenario_status", ""))
        ).strip().upper()
        if scenario_status != "CLASSIFIED":
            excluded["PRESSURE_SCENARIOS_NOT_CLASSIFIED"] += 1
            continue

        preliminary_pool.append(row)

    counts = {
        "input_candidate_count": len(rows),
        "preliminary_evidence_screen_count": len(preliminary_pool),
        "excluded_reason_counts": dict(sorted(excluded.items())),
    }

    if len(preliminary_pool) < 10:
        return _empty_result(
            "INSUFFICIENT EVIDENCE",
            (
                f"Only {len(preliminary_pool)} candidates passed the preliminary evidence screen; "
                "fewer than 10. No Top 10 was emitted. This screen is not final eligibility."
            ),
            discipline=discipline,
            counts=counts,
        )

    # Deliberately fail closed: no weights, thresholds, minimum exposure rule,
    # tie policy, uncertainty estimator or ranking formula has formal approval.
    return _empty_result(
        "METHODOLOGY NOT APPROVED",
        (
            f"{len(preliminary_pool)} candidates passed the preliminary evidence screen, "
            "but there is no approved, versioned ranking methodology. No Top 10 was emitted."
        ),
        discipline=discipline,
        counts=counts,
    )
