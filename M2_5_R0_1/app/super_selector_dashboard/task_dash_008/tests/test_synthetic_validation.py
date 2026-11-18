from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from services.authorization import ProductionExecutionDisabled
from services.scenario_registry import load_scenario_contracts
from task_dash_008.authorization import (
    Stage2AuthorizationError,
    authorization_record_problems,
    authorize_stage2,
    canonical_record_sha256,
    current_authorization_bindings,
)
from task_dash_008.source_adapter import iter_authorized_csv_rows
from task_dash_008.val01_delivery_sequence import validate_delivery_sequence
from task_dash_008.val02_runs_extras import validate_runs_and_extras
from task_dash_008.val03_wickets import validate_wickets
from task_dash_008.val04_batter_opportunity import validate_batter_opportunity
from task_dash_008.val05_bowler_opportunity import validate_bowler_opportunity
from task_dash_008.val06_identity import validate_player_identity
from task_dash_008.val07_target_state import validate_target_state
from task_dash_008.workflow import SyntheticFixtureError, run_synthetic_validation


def delivery(case="base", **overrides):
    row = {
        "fixture_id": f"SYN-{case}", "delivery_id": f"SYN-D-{case}",
        "match_id": "SYN-M1", "innings_id": "SYN-I1", "overid": 1,
        "over_ball_num": 1, "innings_ball_num": 1,
        "runs": 0, "extras_type": None, "extras1_runs": None,
        "extras_2_runs": None, "underlying_legal": None,
        "is_wicket": False, "dismissal_type_id": None,
        "striker_id": "SYN-P1", "non_striker_id": "SYN-P2",
        "bowler_id": "SYN-P3", "striker_team_id": "SYN-T1",
        "non_striker_team_id": "SYN-T1", "bowler_team_id": "SYN-T2",
    }
    row.update(overrides)
    return row


def owner_no_ball():
    return delivery("owner-noball-four", runs=5, extras_type="Overstep", extras1_runs=1, extras_2_runs=4)


def roster():
    return [
        {"match_id": "SYN-M1", "team_id": "SYN-T1", "player_id": "SYN-P1"},
        {"match_id": "SYN-M1", "team_id": "SYN-T1", "player_id": "SYN-P2"},
        {"match_id": "SYN-M1", "team_id": "SYN-T2", "player_id": "SYN-P3"},
    ]


def test_val01_six_normal_deliveries_match_only_synthetic_hypothesis():
    rows = [delivery(str(i), over_ball_num=i, innings_ball_num=i) for i in range(1, 7)]
    result = validate_delivery_sequence(rows)
    assert result.status == "PASS"


def test_val01_extra_deliveries_and_incomplete_final_over_are_not_forced():
    extras = [delivery(str(i), over_ball_num=i, innings_ball_num=i) for i in range(1, 7)]
    extras += [
        delivery("wide", over_ball_num=7, innings_ball_num=7, extras_type="wide", runs=1),
        delivery("noball", over_ball_num=8, innings_ball_num=8, extras_type="Overstep", runs=1, extras1_runs=1, extras_2_runs=0),
    ]
    assert validate_delivery_sequence(extras).status == "PASS"
    seven_legal = [delivery(f"seven{i}", over_ball_num=i, innings_ball_num=i) for i in range(1, 8)]
    assert validate_delivery_sequence(seven_legal).status == "FAIL"
    short = [delivery(f"short{i}", overid=20, over_ball_num=i, innings_ball_num=i) for i in range(1, 5)]
    short.append(delivery("next-innings", innings_id="SYN-I2", overid=1, over_ball_num=1, innings_ball_num=1))
    assert validate_delivery_sequence(short).status == "PASS WITH LIMITATIONS"


def test_val01_duplicate_or_missing_sequence_fails_closed():
    rows = [delivery("a"), delivery("b", innings_ball_num=1)]
    assert validate_delivery_sequence(rows).status == "FAIL"
    missing = [delivery("missing", innings_ball_num=None)]
    assert validate_delivery_sequence(missing).status == "NOT VALIDATED"
    over_gap = [delivery(f"over1-{i}", overid=1, over_ball_num=i, innings_ball_num=i) for i in range(1, 7)]
    over_gap += [delivery("over3", overid=3, over_ball_num=1, innings_ball_num=7)]
    assert validate_delivery_sequence(over_gap).status == "NOT VALIDATED"


@pytest.mark.parametrize(("runs", "penalty", "batter", "expected"), [(5, 1, 4, (4, 5, 5)), (7, 1, 6, (6, 7, 7)), (4, 1, 3, (3, 4, 4))])
def test_val02_owner_no_ball_cases(runs, penalty, batter, expected):
    row = delivery("noball", runs=runs, extras_type="Overstep", extras1_runs=penalty, extras_2_runs=batter)
    result = validate_runs_and_extras([row])
    assert result.status == "PASS"
    assert (result.metrics["batter_runs"], result.metrics["team_runs"], result.metrics["bowler_conceded_runs"]) == expected


def test_val02_unreconciled_and_unknown_extras_are_not_silently_allocated():
    mismatch = validate_runs_and_extras([delivery("mismatch", runs=5, extras_type="Overstep", extras1_runs=1, extras_2_runs=3)])
    assert mismatch.status == "FAIL"
    unknown = validate_runs_and_extras([delivery("unknown", runs=2, extras_type="")])
    assert unknown.status == "NOT VALIDATED"
    assert unknown.metrics["team_runs"] == 2
    assert unknown.metrics["batter_runs"] is None


def test_val02_numeric_csv_text_parses_strictly_without_zero_defaults():
    row = delivery("csv-text", runs="5", extras_type="Overstep", extras1_runs="1", extras_2_runs="4")
    assert validate_runs_and_extras([row]).metrics["team_runs"] == 5
    for invalid in ("", "-1", "1.5", "not-a-number", True):
        malformed = validate_runs_and_extras([delivery(f"invalid-{invalid}", runs=invalid)])
        assert malformed.status == "FAIL"
        assert malformed.metrics["team_runs"] is None


def test_val01_sequence_numbers_can_be_parsed_from_numeric_csv_text():
    rows = [delivery(str(i), over_ball_num=str(i), innings_ball_num=str(i)) for i in range(1, 7)]
    assert validate_delivery_sequence(rows).status == "PASS"


@pytest.mark.parametrize(("category", "batter", "bowler"), [
    ("wide", 0, 2), ("Other", 0, 2), ("byes", 0, 0), ("legbyes", 0, 0),
])
def test_val02_other_extra_allocations(category, batter, bowler):
    row = delivery(category, runs=2, extras_type=category, extras_2_runs=9)
    result = validate_runs_and_extras([row])
    assert result.metrics["batter_runs"] == batter
    assert result.metrics["team_runs"] == 2
    assert result.metrics["bowler_conceded_runs"] == bowler


def test_val03_team_and_bowler_wickets_remain_separate():
    rows = [delivery(f"w{i}", is_wicket=True, dismissal_type_id=i) for i in range(1, 6)]
    result = validate_wickets(rows)
    assert result.metrics == {"team_wickets": 5, "bowler_wickets": 4}
    assert validate_wickets([delivery("missing", is_wicket=True)]).metrics["bowler_wickets"] is None
    assert validate_wickets([delivery("conflict", is_wicket=False, dismissal_type_id=4)]).status == "FAIL"
    assert validate_wickets([delivery("raw-bool", is_wicket="false")]).status == "NOT VALIDATED"


def test_val04_batter_balls_faced_and_unknown_bye_legality():
    rows = [
        delivery("normal"),
        delivery("wide", extras_type="wide"),
        delivery("noball", extras_type="Overstep", runs=1, extras1_runs=1, extras_2_runs=0),
        delivery("other", extras_type="Other"),
    ]
    assert validate_batter_opportunity(rows).metrics["batter_balls_faced"] == 2
    bye = validate_batter_opportunity([delivery("bye", extras_type="byes")])
    assert bye.status == "NOT VALIDATED" and bye.metrics["batter_balls_faced"] is None


def test_val05_bowler_legal_balls_and_conceded_runs():
    rows = [
        delivery("normal", runs=2),
        delivery("noball", runs=5, extras_type="Overstep", extras1_runs=1, extras_2_runs=4),
        delivery("wide", runs=1, extras_type="wide"),
        delivery("bye", runs=2, extras_type="byes", underlying_legal=True),
    ]
    result = validate_bowler_opportunity(rows)
    assert result.metrics == {"bowler_legal_deliveries": 2, "bowler_conceded_runs": 8}


def test_val06_direct_id_join_flags_duplicates_and_unmatched_players():
    assert validate_player_identity([delivery()], roster()).status == "PASS"
    dup = roster() + [dict(roster()[0])]
    assert validate_player_identity([delivery()], dup).status == "FAIL"
    unmatched = delivery("unmatched", striker_id="SYN-NOT-ROSTERED")
    assert validate_player_identity([unmatched], roster()).status == "FAIL"


def test_val07_target_missing_or_revision_unavailable_never_falls_back():
    missing = validate_target_state([])
    assert missing.status == "NOT VALIDATED"
    revised_missing = validate_target_state([{
        "fixture_id": "SYN-TARGET", "match_id": "SYN-M1", "innings_id": "SYN-I2",
        "target_mapping_status": "VALIDATED", "revision_required": True,
        "original_target_runs": 180, "original_target_status": "VERIFIED",
        "revised_target_runs": None, "revision_status": "MISSING", "effective_before_delivery": False,
    }])
    assert revised_missing.status == "NOT VALIDATED"
    valid = validate_target_state([{
        "fixture_id": "SYN-TARGET-OK", "target_mapping_status": "VALIDATED", "revision_required": True,
        "revised_target_runs": 155, "revision_status": "VERIFIED", "effective_before_delivery": True,
    }])
    assert valid.status == "PASS"


def _complete_synthetic_authorization_record():
    bindings = current_authorization_bindings()
    record = {
        "record_id": "SYN-AUTH-1", "stage2_status": "APPROVED", "production_execution_status": "AUTHORIZED",
        "decision_authority": "Project Owner",
        "methodology": {"version": bindings["methodology_version"], "sha256": bindings["methodology_sha256"]},
        "source": bindings["source"],
        "implementation": {"version": bindings["implementation_version"], "code_sha256": bindings["code_sha256"],
                            "dependency_lock_sha256": bindings["dependency_lock_sha256"],
                            "source_contract_sha256": bindings["source_contract_sha256"]},
        "execution_environment": {**bindings["environment"],
                                  "max_runtime_seconds": 10, "max_memory_bytes": 1000,
                                  "max_input_bytes": 1000, "max_output_bytes": 1000},
        "permitted_operations": ["source_row_read_only", "VAL-01"],
        "output_contract": {"directory": str(Path.cwd() / "SYNTHETIC_ONLY"), "schemas": bindings["schemas"], "no_overwrite": True},
        "acceptance_tests": ["synthetic"], "stop_conditions": ["synthetic"],
        "incident_handling": {"policy_id": "synthetic", "contact": "synthetic", "escalation_path": "synthetic"},
        "evidence_retention": {"policy_id": "synthetic", "retention_period": "synthetic", "custodian": "synthetic"},
        "approvals": {role: {"status": "APPROVED", "identity": "synthetic", "evidence_ref": "synthetic"}
                      for role in ("project_owner", "security_authority", "independent_reviewer")},
    }
    record["record_sha256"] = canonical_record_sha256(record)
    return record


def test_gate_denies_missing_and_fabricated_record_while_anchor_is_empty(tmp_path):
    assert "AUTHORIZATION_RECORD_MISSING_OR_NOT_OBJECT" in authorization_record_problems(None)
    record = _complete_synthetic_authorization_record()
    assert authorization_record_problems(record) == ()
    out_of_scope = dict(record)
    out_of_scope["permitted_operations"] = ["player_rankings"]
    out_of_scope["record_sha256"] = canonical_record_sha256(out_of_scope)
    assert "PERMITTED_OPERATION_OUT_OF_SCOPE" in authorization_record_problems(out_of_scope)
    wrong_source = dict(record)
    wrong_source["source"] = {**record["source"], "archive_sha256": "0" * 64}
    wrong_source["record_sha256"] = canonical_record_sha256(wrong_source)
    assert "SOURCE_IDENTITY_NOT_CURRENT" in authorization_record_problems(wrong_source)
    with pytest.raises(Stage2AuthorizationError, match="TRUST_ANCHOR_REGISTRY_EMPTY"):
        authorize_stage2(record)
    impossible_source = tmp_path / "must-not-be-opened.zip"
    with pytest.raises(Stage2AuthorizationError, match="TRUST_ANCHOR_REGISTRY_EMPTY"):
        tuple(iter_authorized_csv_rows(
            authorization_record=record, archive_path=impossible_source,
            expected_archive_size=1, expected_archive_sha256="b" * 64,
            member_name="synthetic.csv", expected_member_size=1, expected_member_sha256="c" * 64,
        ))
    assert not impossible_source.exists()


def test_all_scenarios_and_deferred_states_remain_unchanged():
    contracts = load_scenario_contracts()
    assert len(contracts) == 18
    assert {c.scenario_id for c in contracts} == {f"{d}-S{i:02d}" for d in ("BAT", "BWL") for i in range(1, 10)}
    assert {c.scenario_id for c in contracts if c.readiness_status == "DEFERRED"} == {"BAT-S03", "BWL-S04", "BWL-S08"}


def test_synthetic_workflow_rejects_unlabelled_rows():
    targets = [{"fixture_id": "SYN-TARGET", "target_mapping_status": "MISSING"}]
    results = run_synthetic_validation([delivery()], roster(), targets)
    assert [result.validation_id for result in results] == [f"VAL-0{i}" for i in range(1, 8)]
    with pytest.raises(SyntheticFixtureError, match="DELIVERY_FIXTURE_NOT_EXPLICITLY_SYNTHETIC"):
        run_synthetic_validation([{**delivery(), "fixture_id": "MATCH-1"}], roster(), targets)
