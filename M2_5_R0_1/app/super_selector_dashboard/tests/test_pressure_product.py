import pandas as pd

from services.pressure_product import _attribute, reconstruct_states, classify_scenarios


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
