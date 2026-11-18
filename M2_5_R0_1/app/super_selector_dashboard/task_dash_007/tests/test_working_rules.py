"""All observations here are labelled synthetic and never loaded from files."""

from dataclasses import replace

import pytest

from services.authorization import ProductionExecutionDisabled
from services.scenario_registry import load_scenario_contracts
from task_dash_007.working_rules import (
    SyntheticDelivery,
    SyntheticValidationError,
    attribute_synthetic_delivery,
    evaluate_synthetic_over,
    resolve_synthetic_target,
    validate_match_innings_link,
    validate_player_participation,
)


def d(case: str, runs: int, *, extras_type=None, extras1_runs=None, extras_2_runs=None,
      underlying_legal=None, is_wicket=False, dismissal_type_id=None):
    return SyntheticDelivery(
        f"SYN-{case}", runs, extras_type, extras1_runs, extras_2_runs,
        underlying_legal, is_wicket, dismissal_type_id,
    )


@pytest.mark.parametrize("runs", [0, 1, 2, 3, 4, 6])
def test_ordinary_deliveries_keep_team_batter_bowler_outputs_separate(runs):
    result = attribute_synthetic_delivery(d(f"normal-{runs}", runs, extras_type=None))
    assert (result.batter_runs, result.team_runs, result.bowler_conceded_runs) == (runs, runs, runs)
    assert (result.batter_balls_faced, result.bowler_legal_deliveries) == (1, 1)
    assert result.data_mode == "SYNTHETIC"


@pytest.mark.parametrize(("label", "runs", "penalty", "batter", "expected_batter"), [
    ("noball-four", 5, 1, 4, 4),
    ("noball-six", 7, 1, 6, 6),
    ("noball-extra-batter", 4, 1, 3, 3),
])
def test_no_ball_components_reconcile_without_double_counting(label, runs, penalty, batter, expected_batter):
    result = attribute_synthetic_delivery(d(label, runs, extras_type="Overstep", extras1_runs=penalty, extras_2_runs=batter))
    assert (result.batter_runs, result.team_runs, result.bowler_conceded_runs) == (expected_batter, runs, runs)
    assert (result.batter_balls_faced, result.bowler_legal_deliveries) == (1, 0)


@pytest.mark.parametrize("extras_type,runs,underlying,expected_faced,expected_legal,expected_batter,expected_bowler", [
    ("wide", 1, None, 0, 0, 0, 1),
    ("byes", 2, True, 1, 1, 0, 0),
    ("byes", 2, False, 0, 0, 0, 0),
    ("legbyes", 1, True, 1, 1, 0, 0),
    ("legbyes", 1, False, 0, 0, 0, 0),
])
def test_wide_bye_and_legbye_follow_working_ball_attribution(extras_type, runs, underlying, expected_faced, expected_legal, expected_batter, expected_bowler):
    result = attribute_synthetic_delivery(d(f"extra-{extras_type}-{underlying}", runs, extras_type=extras_type, underlying_legal=underlying))
    assert (result.batter_runs, result.team_runs, result.bowler_conceded_runs) == (expected_batter, runs, expected_bowler)
    assert (result.batter_balls_faced, result.bowler_legal_deliveries) == (expected_faced, expected_legal)


@pytest.mark.parametrize("other_runs,team_runs", [(4, 5), (2, 3)])
def test_other_extras_component_is_excluded_from_batter_regardless_of_value(other_runs, team_runs):
    result = attribute_synthetic_delivery(d(f"other-{other_runs}", team_runs, extras_type="Other", extras_2_runs=other_runs))
    assert result.batter_runs == 0
    assert result.team_runs == team_runs
    assert result.bowler_conceded_runs == team_runs
    assert (result.batter_balls_faced, result.bowler_legal_deliveries) == (0, 0)


def test_no_ball_run_components_that_do_not_sum_to_delivery_runs_are_flagged():
    result = attribute_synthetic_delivery(d("noball-mismatch", 5, extras_type="Overstep", extras1_runs=1, extras_2_runs=3))
    assert result.status == "INVALID"
    assert result.team_runs == 5
    assert result.batter_runs is None and result.bowler_conceded_runs is None
    assert "RUN_COMPONENTS_DO_NOT_RECONCILE" in result.reason_codes


def test_unknown_extra_category_is_not_normalized_or_assigned():
    result = attribute_synthetic_delivery(d("unknown-extra", 2, extras_type="WIDE"))
    assert result.status == "NOT_VERIFIABLE"
    assert result.team_runs == 2
    assert result.batter_runs is None and result.bowler_conceded_runs is None
    assert "UNKNOWN_EXTRAS_CATEGORY" in result.reason_codes


def test_bye_without_underlying_legal_status_keeps_ball_counts_unknown():
    result = attribute_synthetic_delivery(d("bye-unknown-legal", 1, extras_type="byes"))
    assert result.batter_runs == 0 and result.team_runs == 1 and result.bowler_conceded_runs == 0
    assert result.batter_balls_faced is None and result.bowler_legal_deliveries is None
    assert "UNDERLYING_DELIVERY_STATUS_UNVERIFIED" in result.reason_codes


@pytest.mark.parametrize("dismissal_id,expected_bowler_wicket", [(1, 1), (2, 1), (3, 1), (4, 0), (5, 1)])
def test_provided_dismissal_ids_map_to_team_and_bowler_wickets(dismissal_id, expected_bowler_wicket):
    result = attribute_synthetic_delivery(d(f"wicket-{dismissal_id}", 0, is_wicket=True, dismissal_type_id=dismissal_id))
    assert result.team_wickets == 1
    assert result.bowler_wickets == expected_bowler_wicket


def test_missing_and_unknown_dismissal_ids_do_not_invent_bowler_credit():
    missing = attribute_synthetic_delivery(d("wicket-missing-id", 0, is_wicket=True))
    unknown = attribute_synthetic_delivery(d("wicket-unknown-id", 0, is_wicket=True, dismissal_type_id=99))
    assert missing.team_wickets == unknown.team_wickets == 1
    assert missing.bowler_wickets is None and unknown.bowler_wickets is None
    assert "DISMISSAL_ID_MISSING" in missing.reason_codes
    assert "DISMISSAL_ID_UNSUPPORTED" in unknown.reason_codes


def test_dismissal_code_without_team_wicket_flag_is_contradictory():
    result = attribute_synthetic_delivery(d("contradictory-wicket", 0, is_wicket=False, dismissal_type_id=1))
    assert result.status == "INVALID"
    assert result.team_wickets == 0 and result.bowler_wickets is None
    assert "DISMISSAL_ID_WITHOUT_WICKET_FLAG" in result.reason_codes


def test_dismissal_id_is_not_treated_as_numeric_wicket_count():
    result = attribute_synthetic_delivery(d("string-dismissal-id", 0, is_wicket=True, dismissal_type_id="1"))
    assert result.team_wickets == 1 and result.bowler_wickets is None
    assert "DISMISSAL_ID_INVALID_TYPE" in result.reason_codes


def over_rows(case, categories):
    rows = []
    for index, (category, legal) in enumerate(categories, start=1):
        delivery = d(f"{case}-{index}", 0 if category is None else 1, extras_type=category,
                     extras1_runs=1 if category == "Overstep" else None,
                     extras_2_runs=0 if category == "Overstep" else None,
                     underlying_legal=legal)
        rows.append({"fixture_id": f"SYN-{case}-{index}", "match_id": "SYN-M1", "innings_id": "SYN-I1",
                     "over_id": "SYN-O1", "over_ball_num": index, "delivery": delivery})
    return rows


def test_six_delivery_over_matches_hypothesis_in_synthetic_case():
    rows = over_rows("six-ball-over", [(None, None)] * 6)
    result = evaluate_synthetic_over(rows, following_match_id="SYN-M1", following_innings_id="SYN-I1", following_over_id="SYN-O2")
    assert result.status == "HYPOTHESIS_MATCHES_SYNTHETIC_CASE"
    assert result.legal_deliveries == 6


def test_over_ending_above_six_and_multiple_extra_deliveries_reconcile():
    categories = [(None, None)] * 6 + [("wide", None), ("Overstep", None)]
    rows = over_rows("multi-extra-over", categories)
    result = evaluate_synthetic_over(rows, following_match_id="SYN-M1", following_innings_id="SYN-I1", following_over_id="SYN-O2")
    assert result.status == "HYPOTHESIS_MATCHES_SYNTHETIC_CASE"
    assert result.legal_deliveries == 6


def test_incomplete_final_over_is_identified_by_innings_transition():
    rows = over_rows("incomplete-final", [(None, None)] * 4)
    result = evaluate_synthetic_over(rows, following_match_id="SYN-M1", following_innings_id="SYN-M2-I2")
    assert result.status == "INCOMPLETE_FINAL_OVER"
    assert result.legal_deliveries == 4
    assert "INNINGS_TRANSITION_IDENTIFIES_FINAL_OVER" in result.reason_codes


def test_six_ball_number_with_wide_category_contradicts_hypothesis():
    rows = over_rows("six-with-wide", [(None, None)] * 5 + [("wide", None)])
    result = evaluate_synthetic_over(rows, following_match_id="SYN-M1", following_innings_id="SYN-I1", following_over_id="SYN-O2")
    assert result.status == "CONTRADICTED"
    assert result.legal_deliveries == 5


def test_more_than_six_without_extra_deliveries_is_flagged():
    rows = over_rows("seven-legal", [(None, None)] * 7)
    result = evaluate_synthetic_over(rows, following_match_id="SYN-M1", following_innings_id="SYN-I1", following_over_id="SYN-O2")
    assert result.status == "CONTRADICTED"
    assert result.legal_deliveries == 7


def test_unknown_extra_in_over_does_not_silently_determine_legal_balls():
    rows = over_rows("unknown-over-category", [(None, None)] * 5 + [("WIDE", None)])
    result = evaluate_synthetic_over(rows, following_match_id="SYN-M1", following_innings_id="SYN-I1", following_over_id="SYN-O2")
    assert result.status == "NOT_VERIFIABLE"
    assert result.legal_deliveries is None


def test_direct_player_id_matching_and_unmatched_id():
    playing = [{"match_id": "SYN-M1", "team_id": "SYN-T1", "player_id": "SYN-P1", "player_name": "Same Name"}]
    assert validate_player_participation(player_id="SYN-P1", match_id="SYN-M1", team_id="SYN-T1", playing_eleven=playing) == ("MATCHED", "DIRECT_STABLE_ID_MATCH")
    assert validate_player_participation(player_id="SYN-P2", match_id="SYN-M1", team_id="SYN-T1", playing_eleven=playing)[0] == "UNMATCHED"


def test_duplicate_participation_and_missing_ids_are_explicit():
    row = {"match_id": "SYN-M1", "team_id": "SYN-T1", "player_id": "SYN-P1"}
    status, code = validate_player_participation(player_id="SYN-P1", match_id="SYN-M1", team_id="SYN-T1", playing_eleven=[row, dict(row)])
    assert (status, code) == ("AMBIGUOUS", "DUPLICATE_MATCH_TEAM_PLAYER_PARTICIPATION")
    assert validate_player_participation(player_id=None, match_id="SYN-M1", team_id="SYN-T1", playing_eleven=[row])[0] == "NOT_VERIFIABLE"


def test_match_innings_identity_link_is_exact():
    assert validate_match_innings_link(match_id="SYN-M1", innings_id="SYN-I1", match_innings=[("SYN-M1", "SYN-I1")]) == ("MATCHED", "DIRECT_MATCH_INNINGS_LINK")
    assert validate_match_innings_link(match_id="SYN-M1", innings_id="SYN-I2", match_innings=[("SYN-M1", "SYN-I1")])[0] == "UNMATCHED"


def test_missing_revised_target_never_falls_back_to_original():
    target = resolve_synthetic_target(original_target=180, original_status="VERIFIED", revision_required=True,
                                      revised_target=None, revision_status="VERIFIED")
    assert target.target is None
    assert target.status == "NOT_VERIFIABLE"
    assert target.reason_code == "REVISED_TARGET_MISSING_OR_INVALID"


def test_missing_original_target_is_not_inferred():
    target = resolve_synthetic_target(original_target=None, original_status="MISSING", revision_required=False)
    assert target.target is None and target.status == "NOT_VERIFIABLE"


def test_production_mode_is_denied_before_evaluation():
    with pytest.raises(ProductionExecutionDisabled, match="Stage 2 NOT GRANTED"):
        attribute_synthetic_delivery(None, data_mode="PRODUCTION")


def test_scenario_registry_and_deferred_readiness_are_unchanged():
    contracts = load_scenario_contracts()
    assert len(contracts) == 18
    assert {x.scenario_id for x in contracts} == {f"{d}-S{i:02d}" for d in ("BAT", "BWL") for i in range(1, 10)}
    deferred = {x.scenario_id for x in contracts if x.readiness_status == "DEFERRED"}
    assert deferred == {"BAT-S03", "BWL-S04", "BWL-S08"}

