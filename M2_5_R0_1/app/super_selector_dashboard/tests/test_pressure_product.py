import pandas as pd

from services.pressure_product import _attribute, reconstruct_states, classify_scenarios, prior_baselines, _rank


def test_extras_attribution_reconciles_or_explicitly_excludes():
    rows = pd.DataFrame([
        {"runs_n": 0, "extras1_runs_n": 1, "extras_2_runs_n": 0, "extras_type": "wide", "is_wicket_b": False, "dismissal_type_id_n": None, "dismissed_player_id": ""},
        {"runs_n": 5, "extras1_runs_n": 1, "extras_2_runs_n": 4, "extras_type": "Overstep", "is_wicket_b": False, "dismissal_type_id_n": None, "dismissed_player_id": ""},
        {"runs_n": 4, "extras1_runs_n": 1, "extras_2_runs_n": 0, "extras_type": "Overstep", "is_wicket_b": False, "dismissal_type_id_n": None, "dismissed_player_id": ""},
        {"runs_n": 0, "extras1_runs_n": 2, "extras_2_runs_n": 0, "extras_type": "byes", "is_wicket_b": False, "dismissal_type_id_n": None, "dismissed_player_id": ""},
    ])
    result = _attribute(rows)
    assert result.attribution_status.tolist() == ["RECONCILED", "RECONCILED", "UNRESOLVED_SOURCE_SEMANTICS", "RECONCILED"]
    assert result.loc[0, "team_runs_calc"] == 1 and result.loc[0, "batter_faced"] == 0
    assert result.loc[1, "team_runs_calc"] == 5 and result.loc[1, "batter_runs_calc"] == 4 and result.loc[1, "legal_ball"] == 0
    assert pd.isna(result.loc[2, "team_runs_calc"])
    assert result.loc[3, "team_runs_calc"] == 2 and result.loc[3, "bowler_runs_calc"] == 0


def test_state_is_strictly_pre_delivery_and_invalid_outcome_only_affects_later_state():
    rows = pd.DataFrame([
        {"match_id": "M1", "innings": "1", "innings_n": 1, "sequence": i, "innings_ball_num": i, "overid_n": 1,
         "striker_id": "P1", "striker_name": "A", "non_striker_id": "P2", "non_striker_name": "B",
         "bowler_id": "P3", "bowler_name": "C", "batting_team_id": "T1", "bowling_team_id": "T2",
         "season": 2022, "delivery_ist_time": f"2022-01-01T00:0{i}:00Z", "team_runs_calc": runs,
         "batter_runs_calc": runs, "bowler_runs_calc": runs, "batter_faced": 1, "legal_ball": 1,
         "attribution_status": status, "team_wicket": False, "is_wicket_b": False,
         "bowler_credit_wicket": False, "dismissal_type_id_n": None}
        for i, (runs, status) in enumerate([(4, "RECONCILED"), (None, "UNRESOLVED_SOURCE_SEMANTICS"), (1, "RECONCILED")], 1)
    ])
    matches = pd.DataFrame([{"match_id": "M1", "season": 2022, "revised_target": "", "first_inn_revised_overs": "", "second_inn_revised_overs": ""}])
    playing = pd.DataFrame([
        {"match_id": "M1", "team_id": "T1", "player_id": "P1", "batting_order": 1},
        {"match_id": "M1", "team_id": "T1", "player_id": "P2", "batting_order": 2},
    ])
    states = reconstruct_states(rows, matches, playing)
    assert states.score_before.tolist()[:2] == [0, 4]
    assert states.delivery_team_runs.iloc[0] == 4
    assert states.state_status.tolist() == ["RECONSTRUCTED", "RECONSTRUCTED", "PARTIAL_OR_UNRESOLVED"]
    classified = classify_scenarios(states)
    assert classified.pressure.tolist() == [False, False, False]
    assert classified.B1.tolist() == [False, False, False]


def test_prior_baseline_excludes_current_delivery():
    rows = pd.DataFrame([
        {"delivery_ist_time": f"2022-01-01T00:0{i}:00Z", "match_id": "M", "innings_n": 1, "sequence": i,
         "striker_id": "B", "bowler_id": "W", "delivery_batter_runs": runs, "batter_faced": 1,
         "delivery_bowler_runs": runs, "legal_ball": 1}
        for i, runs in enumerate([4, 0, 6], 1)
    ])
    result = prior_baselines(rows)
    assert result.bat_prior_exposure.tolist() == [0, 1, 2]
    assert pd.isna(result.bat_prior_rate.iloc[0])
    assert result.bat_prior_rate.iloc[1] == 4
    assert result.bat_prior_rate.iloc[2] == 2


def test_provisional_rank_is_automatic_deterministic_and_applies_evidence_floor():
    candidates = pd.DataFrame([
        {"player_id": "A", "matches": 8, "opportunities": 50, "baseline_events": 50, "delta_vs_prior": 5.0, "scenario_coverage": 4, "pressure_strike_rate": 150},
        {"player_id": "B", "matches": 6, "opportunities": 35, "baseline_events": 35, "delta_vs_prior": 8.0, "scenario_coverage": 3, "pressure_strike_rate": 140},
        {"player_id": "C", "matches": 2, "opportunities": 12, "baseline_events": 12, "delta_vs_prior": 99.0, "scenario_coverage": 2, "pressure_strike_rate": 200},
    ])
    ranked = _rank(candidates, "batting")
    assert ranked.player_id.tolist() == ["B", "A"]
    assert ranked["rank"].tolist() == [1, 2]
    assert "C" not in ranked.player_id.tolist()
