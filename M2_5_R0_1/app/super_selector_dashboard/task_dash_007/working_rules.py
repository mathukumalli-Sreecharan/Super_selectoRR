"""Synthetic-only reference checks for pending Project Owner working rules.

Nothing in this module is a provider-verified source definition or a
production calculation. The functions require explicitly labelled synthetic
fixtures and preserve unsupported or contradictory evidence as unresolved.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

_V015_ROOT = Path(__file__).resolve().parents[1] / "versions" / "TASK_DASH_002_implementation_v0_1_5"
if str(_V015_ROOT) not in sys.path:
    sys.path.insert(0, str(_V015_ROOT))
from services.authorization import PRODUCTION_GATE  # noqa: E402


EXTRAS_CATEGORIES = {"wide", "Overstep", "byes", "legbyes", "Other"}
BOWLER_WICKET_CREDIT = {1: 1, 2: 1, 3: 1, 4: 0, 5: 1}


class SyntheticValidationError(ValueError):
    """Malformed synthetic fixture rejected without coercion."""


@dataclass(frozen=True)
class SyntheticDelivery:
    fixture_id: str
    runs: Any
    extras_type: Any = None
    extras1_runs: Any = None
    extras_2_runs: Any = None
    underlying_legal: Any = None
    is_wicket: Any = None
    dismissal_type_id: Any = None


@dataclass(frozen=True)
class DeliveryAttribution:
    fixture_id: str
    team_runs: int | None
    batter_runs: int | None
    bowler_conceded_runs: int | None
    batter_balls_faced: int | None
    bowler_legal_deliveries: int | None
    team_wickets: int | None
    bowler_wickets: int | None
    status: str
    reason_codes: tuple[str, ...]
    data_mode: str = "SYNTHETIC"


@dataclass(frozen=True)
class OverSequenceResult:
    match_id: str
    innings_id: str
    over_id: str
    status: str
    legal_deliveries: int | None
    reason_codes: tuple[str, ...]
    data_mode: str = "SYNTHETIC"


@dataclass(frozen=True)
class TargetAvailability:
    target: int | None
    status: str
    reason_code: str | None
    data_mode: str = "SYNTHETIC"


def _mode_guard(data_mode: str) -> None:
    if data_mode != "SYNTHETIC":
        PRODUCTION_GATE.require_production_authorization("evaluate source working definitions")


def attribute_synthetic_delivery(
    delivery: SyntheticDelivery,
    *,
    data_mode: str = "SYNTHETIC",
) -> DeliveryAttribution:
    """Evaluate only an explicit synthetic case under supplied working rules."""
    _mode_guard(data_mode)
    if not isinstance(delivery, SyntheticDelivery) or not delivery.fixture_id.startswith("SYN-"):
        raise SyntheticValidationError("Only explicitly SYN- labelled synthetic delivery fixtures are accepted.")

    reasons: list[str] = []
    invalid = False
    unverifiable = False
    if type(delivery.runs) is not int or delivery.runs < 0:
        return DeliveryAttribution(delivery.fixture_id, None, None, None, None, None, None, None, "INVALID", ("INVALID_TEAM_RUNS",))

    team_runs: int | None = delivery.runs  # Owner working definition: count `runs` once; never add extras again.
    batter_runs: int | None = None
    bowler_runs: int | None = None
    faced: int | None = None
    legal: int | None = None

    category = delivery.extras_type
    if category is None:
        # None means an explicit synthetic "no extras" assertion only. It is
        # not a mapping for a blank production CSV cell.
        components = (delivery.extras1_runs, delivery.extras_2_runs)
        if any(value not in (None, 0) for value in components):
            reasons.append("NO_EXTRAS_COMPONENT_CONFLICT")
            invalid = True
        else:
            batter_runs = delivery.runs
            bowler_runs = delivery.runs
            faced = legal = 1
    elif category not in EXTRAS_CATEGORIES:
        reasons.append("UNKNOWN_EXTRAS_CATEGORY")
        unverifiable = True
    elif category == "Overstep":
        faced, legal = 1, 0
        penalty, batter_component = delivery.extras1_runs, delivery.extras_2_runs
        if penalty is None or batter_component is None:
            reasons.append("NOBALL_COMPONENTS_MISSING")
            unverifiable = True
        elif any(type(value) is not int or value < 0 for value in (penalty, batter_component)):
            reasons.append("INVALID_NOBALL_COMPONENT")
            invalid = True
        elif penalty + batter_component != delivery.runs:
            reasons.append("RUN_COMPONENTS_DO_NOT_RECONCILE")
            invalid = True
        else:
            batter_runs = batter_component
            bowler_runs = delivery.runs
    elif category == "wide":
        batter_runs, bowler_runs = 0, delivery.runs
        faced, legal = 0, 0
    elif category == "Other":
        batter_runs, bowler_runs = 0, delivery.runs
        faced, legal = 0, 0
    elif category in {"byes", "legbyes"}:
        batter_runs, bowler_runs = 0, 0
        if type(delivery.underlying_legal) is not bool:
            reasons.append("UNDERLYING_DELIVERY_STATUS_UNVERIFIED")
            unverifiable = True
        else:
            faced = legal = int(delivery.underlying_legal)

    team_wickets: int | None
    bowler_wickets: int | None
    if type(delivery.is_wicket) is not bool:
        team_wickets = bowler_wickets = None
        reasons.append("IS_WICKET_INVALID_OR_MISSING")
        invalid = True
    elif not delivery.is_wicket:
        team_wickets = 0
        if delivery.dismissal_type_id is not None:
            bowler_wickets = None
            reasons.append("DISMISSAL_ID_WITHOUT_WICKET_FLAG")
            invalid = True
        else:
            bowler_wickets = 0
    else:
        team_wickets = 1
        dismissal_id = delivery.dismissal_type_id
        if dismissal_id is None:
            bowler_wickets = None
            reasons.append("DISMISSAL_ID_MISSING")
            unverifiable = True
        elif type(dismissal_id) is not int:
            bowler_wickets = None
            reasons.append("DISMISSAL_ID_INVALID_TYPE")
            invalid = True
        elif dismissal_id not in BOWLER_WICKET_CREDIT:
            bowler_wickets = None
            reasons.append("DISMISSAL_ID_UNSUPPORTED")
            unverifiable = True
        else:
            bowler_wickets = BOWLER_WICKET_CREDIT[dismissal_id]

    status = "INVALID" if invalid else "NOT_VERIFIABLE" if unverifiable else "SYNTHETIC_RULE_CASE_PASS"
    return DeliveryAttribution(
        delivery.fixture_id, team_runs, batter_runs, bowler_runs, faced, legal,
        team_wickets, bowler_wickets, status, tuple(dict.fromkeys(reasons)),
    )


def evaluate_synthetic_over(
    deliveries: Sequence[Mapping[str, Any]],
    *,
    following_match_id: str | None,
    following_innings_id: str | None,
    following_over_id: str | None = None,
    data_mode: str = "SYNTHETIC",
) -> OverSequenceResult:
    """Test the proposed over-ball hypothesis; never certify source legality."""
    _mode_guard(data_mode)
    if not deliveries:
        raise SyntheticValidationError("Over fixture must contain at least one synthetic delivery.")
    head = deliveries[0]
    fixture_id = head.get("fixture_id", "")
    match_id, innings_id, over_id = head.get("match_id"), head.get("innings_id"), head.get("over_id")
    reasons: list[str] = []
    if not str(fixture_id).startswith("SYN-"):
        raise SyntheticValidationError("Over fixtures must be explicitly SYN- labelled.")
    if not all((match_id, innings_id, over_id)):
        return OverSequenceResult(str(match_id), str(innings_id), str(over_id), "INVALID", None, ("OVER_IDENTITY_MISSING",))
    nums = [row.get("over_ball_num") for row in deliveries]
    if any(type(value) is not int or value < 1 for value in nums):
        return OverSequenceResult(match_id, innings_id, over_id, "INVALID", None, ("OVER_BALL_NUMBER_INVALID",))
    if nums != list(range(1, len(nums) + 1)):
        return OverSequenceResult(match_id, innings_id, over_id, "INVALID", None, ("OVER_BALL_ORDER_INCOMPLETE_OR_AMBIGUOUS",))
    if any((row.get("match_id"), row.get("innings_id"), row.get("over_id")) != (match_id, innings_id, over_id) for row in deliveries):
        return OverSequenceResult(match_id, innings_id, over_id, "INVALID", None, ("MIXED_OVER_IDENTITY",))
    evaluations = [attribute_synthetic_delivery(row["delivery"], data_mode=data_mode) for row in deliveries]
    if any(result.bowler_legal_deliveries is None for result in evaluations):
        return OverSequenceResult(match_id, innings_id, over_id, "NOT_VERIFIABLE", None, ("LEGAL_DELIVERY_STATUS_UNAVAILABLE",))
    legal_count = sum(result.bowler_legal_deliveries or 0 for result in evaluations)
    transition = following_match_id == match_id and following_innings_id not in (None, innings_id)
    followed_by_over = following_match_id == match_id and following_innings_id == innings_id and following_over_id not in (None, over_id)
    if following_match_id is not None and following_match_id != match_id:
        reasons.append("FOLLOWING_EVENT_MATCH_MISMATCH")
        return OverSequenceResult(match_id, innings_id, over_id, "INVALID", legal_count, tuple(reasons))

    if nums[-1] == 6:
        if len(deliveries) != 6 or legal_count != 6:
            reasons.append("OVER_ENDS_AT_SIX_HYPOTHESIS_CONFLICTS_WITH_CATEGORIES")
            return OverSequenceResult(match_id, innings_id, over_id, "CONTRADICTED", legal_count, tuple(reasons))
        return OverSequenceResult(match_id, innings_id, over_id, "HYPOTHESIS_MATCHES_SYNTHETIC_CASE", legal_count, ())
    if nums[-1] > 6:
        if transition and legal_count < 6:
            return OverSequenceResult(match_id, innings_id, over_id, "INCOMPLETE_FINAL_OVER", legal_count, ("INNINGS_TRANSITION_IDENTIFIES_FINAL_OVER",))
        if legal_count == 6 and (transition or followed_by_over):
            return OverSequenceResult(match_id, innings_id, over_id, "HYPOTHESIS_MATCHES_SYNTHETIC_CASE", legal_count, ())
        if legal_count != 6 and (transition or followed_by_over):
            return OverSequenceResult(match_id, innings_id, over_id, "CONTRADICTED", legal_count, ("OVER_WITH_EXTRA_DELIVERIES_DOES_NOT_RECONCILE_TO_SIX_LEGAL",))
    if transition and legal_count < 6:
        return OverSequenceResult(match_id, innings_id, over_id, "INCOMPLETE_FINAL_OVER", legal_count, ("INNINGS_TRANSITION_IDENTIFIES_FINAL_OVER",))
    if not transition and not followed_by_over:
        reasons.append("NEXT_EVENT_REQUIRED_TO_CONFIRM_OVER_COMPLETION")
    else:
        reasons.append("OVER_SEQUENCE_DOES_NOT_MATCH_WORKING_HYPOTHESIS")
    return OverSequenceResult(match_id, innings_id, over_id, "NOT_VERIFIABLE", legal_count, tuple(reasons))


def validate_player_participation(
    *, player_id: Any, match_id: Any, team_id: Any, playing_eleven: Sequence[Mapping[str, Any]]
) -> tuple[str, str]:
    """Direct stable-ID match only; names are not inspected."""
    if player_id in (None, "") or match_id in (None, "") or team_id in (None, ""):
        return "NOT_VERIFIABLE", "PLAYER_MATCH_OR_TEAM_ID_MISSING"
    matches = [row for row in playing_eleven if row.get("player_id") == player_id and row.get("match_id") == match_id and row.get("team_id") == team_id]
    if not matches:
        return "UNMATCHED", "PLAYER_ID_NOT_IN_MATCH_TEAM_PARTICIPATION"
    if len(matches) > 1:
        return "AMBIGUOUS", "DUPLICATE_MATCH_TEAM_PLAYER_PARTICIPATION"
    return "MATCHED", "DIRECT_STABLE_ID_MATCH"


def validate_match_innings_link(
    *, match_id: Any, innings_id: Any, match_innings: Sequence[tuple[Any, Any]]
) -> tuple[str, str]:
    if match_id in (None, "") or innings_id in (None, ""):
        return "NOT_VERIFIABLE", "MATCH_OR_INNINGS_ID_MISSING"
    if (match_id, innings_id) not in set(match_innings):
        return "UNMATCHED", "MATCH_INNINGS_LINK_NOT_FOUND"
    return "MATCHED", "DIRECT_MATCH_INNINGS_LINK"


def resolve_synthetic_target(
    *,
    original_target: Any,
    original_status: str,
    revision_required: bool,
    revised_target: Any = None,
    revision_status: str | None = None,
) -> TargetAvailability:
    """Use a revised target only when explicitly required and verified."""
    if revision_required:
        if revision_status != "VERIFIED":
            return TargetAvailability(None, "NOT_VERIFIABLE", "REVISED_TARGET_EVIDENCE_UNVERIFIED")
        target = revised_target
        if type(target) is not int or target <= 0:
            return TargetAvailability(None, "NOT_VERIFIABLE", "REVISED_TARGET_MISSING_OR_INVALID")
        return TargetAvailability(target, "AVAILABLE_SYNTHETIC", None)
    if original_status != "VERIFIED" or type(original_target) is not int or original_target <= 0:
        return TargetAvailability(None, "NOT_VERIFIABLE", "ORIGINAL_TARGET_MISSING_OR_UNVERIFIED")
    return TargetAvailability(original_target, "AVAILABLE_SYNTHETIC", None)
