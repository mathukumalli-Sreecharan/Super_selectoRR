"""Real IPL delivery analytics. Operational rules are provisional and versioned."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from services.production_loader import ARCHIVE_PATH, iter_strict_csv_member, verify_member_metadata

DATA_VERSION = "ipl-source-archive-a992ecd8"
METHODOLOGY_VERSION = "pressure-research-provisional-v0.1.0"
SEASONS = list(range(2022, 2027))
OUT = Path(__file__).resolve().parents[1] / "data" / "exports"

# Research candidate, not owner-approved. Sensitivity variants are included in exports.
METHODOLOGY = {
    "data_version": DATA_VERSION,
    "methodology_version": METHODOLOGY_VERSION,
    "population": "Competitions exactly named IPL 2022 through IPL 2026; exact competition and match IDs.",
    "provisional_pressure_rule": {
        "chase": "required run rate >= that season's mean first-innings scoring rate and wickets remaining <= 8",
        "first_innings": "at least 4 wickets lost by legal ball 60, or at least 6 by legal ball 90",
        "band": "binary research flag; continuous required-rate and wickets-remaining fields retained",
        "rationale": "Uses season-specific observed first-innings scoring rate as a chase benchmark and explicit resource-loss states. This is a candidate operational definition, not formally approved.",
    },
    "pressure_sensitivity": {
        "looser": "chase required rate >=0.9 x season benchmark and wickets remaining<=8; first innings >=3 wickets before legal ball 60 or >=5 before legal ball 90",
        "primary": "chase required rate >=1.0 x season benchmark and wickets remaining<=8; first innings >=4 wickets before legal ball 60 or >=6 before legal ball 90",
        "stricter": "chase required rate >=1.25 x season benchmark and wickets remaining<=6; first innings >=5 wickets before legal ball 60 or >=7 before legal ball 90",
    },
    "scenarios": {
        "B1": "legal balls before delivery <36 and wickets lost >=2",
        "B2": "36<=legal balls<90",
        "B3": "legal balls>=90 and wickets remaining>=5",
        "B4": "legal balls>=90 and two wickets fell in preceding 12 legal balls",
        "B5": "valid chase, RRR>=season mean first-innings rate, wickets remaining<=5",
        "B6": "B5 comparisons stratified by wickets remaining (1-3 versus 4-5)",
        "B7": "striker batting_order<=3 and non-striker batting_order>=6, from pre-delivery lineup order",
        "B8": "at least one wicket in preceding 12 legal balls",
        "B9": "legal balls remaining<=30",
        "B10": "change in defined pressure flag from previous delivery; outcome and pre-state separately retained",
        "W1": "bowling in first 36 legal balls",
        "W2": "bowler-credit dismissal with partnership >=20 runs before delivery",
        "W3": "legal balls remaining<=30",
        "W4": "Batter innings 2 and legal balls before delivery<36",
        "W5": "Batter innings 2 and 36<=legal balls<90",
        "W6": "Batter innings 2 and legal balls remaining<=30",
    },
    "known_limits": [
        "Source run field semantics conflict with the supplied interpretation on extras rows; mismatching rows are excluded from state reconstruction.",
        "2026 season is included exactly as present in the archive; the source snapshot date is not supplied.",
        "B2 role is not inferred as anchor/aggressor; role is unavailable as a validated pre-event field.",
        "Partnership and recent-wicket states are delivery reconstructed; DLS effective time is unavailable, so revised-target matches are excluded from chase classification.",
        "Ranks are descriptive pressure-performance orderings and do not claim causal or uncertainty-adjusted player quality.",
    ],
}


def _read(name: str) -> pd.DataFrame:
    return pd.DataFrame(iter_strict_csv_member(ARCHIVE_PATH, name))


def load_population():
    integrity = verify_member_metadata(ARCHIVE_PATH)
    comps, matches, d = _read("competitions.csv"), _read("matches.csv"), _read("6af855c0e8386_ball_by_ball.csv")
    playing = _read("playing_eleven.csv")
    mapping = _read("competition_team_player_mapping.csv")
    teams = _read("teams.csv")
    all_match_count, all_delivery_count = int(matches.match_id.nunique()), len(d)
    comps["season_num"] = pd.to_numeric(comps.season, errors="coerce")
    comps = comps[comps.comp_name.str.fullmatch(r"IPL 202[2-6]", na=False)].copy()
    comps = comps[comps.season_num.isin(SEASONS)]
    matches = matches[matches.comp_id.astype(str).isin(comps.comp_id.astype(str))].copy()
    d = d[d.match_id.astype(str).isin(matches.match_id.astype(str))].copy()
    playing = playing[playing.match_id.astype(str).isin(matches.match_id.astype(str))].copy()
    mapping = mapping[mapping.comp_id.astype(str).isin(comps.comp_id.astype(str))].copy()
    teams = teams[teams.comp_id.astype(str).isin(comps.comp_id.astype(str))].copy()
    matches["season"] = matches.comp_id.map(comps.set_index("comp_id").season).astype(int)
    d["sequence"] = pd.to_numeric(d.innings_ball_num, errors="coerce")
    for col in ["innings", "overid", "over_ball_num", "runs", "extras1_runs", "extras_2_runs", "dismissal_type_id", "batting_order"]:
        if col in d:
            d[col + "_n"] = pd.to_numeric(d[col], errors="coerce")
    d["is_wicket_b"] = d.is_wicket.astype(str).str.lower().isin(["true", "1", "yes"])
    d["season"] = d.match_id.map(matches.set_index("match_id").season)
    d["comp_id"] = d.match_id.map(matches.set_index("match_id").comp_id)
    # Audit exact all-field and delivery-key duplicates before any aggregation.
    duplicate_exact = int(d.duplicated().sum())
    duplicate_key = int(d.duplicated(["match_id", "innings", "innings_ball_num"]).sum())
    return integrity, comps, matches, d, playing, mapping, teams, duplicate_exact, duplicate_key, all_match_count, all_delivery_count


def _attribute(d: pd.DataFrame) -> pd.DataFrame:
    x = d.copy()
    ex = x.extras_type.fillna("").astype(str).str.strip().str.lower()
    runs = x.runs_n
    e1, e2 = x.extras1_runs_n, x.extras_2_runs_n
    known_normal = ex.isin(["", "none", "nan", "null"])
    valid = pd.Series(True, index=x.index)
    x["team_runs_calc"] = np.nan
    x["batter_runs_calc"] = np.nan
    x["bowler_runs_calc"] = np.nan
    x["batter_faced"] = np.nan
    x["legal_ball"] = np.nan
    x.loc[known_normal, ["team_runs_calc", "batter_runs_calc", "bowler_runs_calc"]] = np.repeat(runs[known_normal].to_numpy()[:, None], 3, axis=1)
    x.loc[known_normal, "batter_faced"] = 1
    x.loc[known_normal, "legal_ball"] = 1
    wide = ex.eq("wide")
    x.loc[wide, "team_runs_calc"] = e1[wide]
    x.loc[wide, "bowler_runs_calc"] = e1[wide]
    x.loc[wide, "batter_runs_calc"] = 0
    x.loc[wide, "batter_faced"] = 0
    x.loc[wide, "legal_ball"] = 0
    bye = ex.isin(["byes", "legbyes"])
    x.loc[bye, "team_runs_calc"] = e1[bye]
    x.loc[bye, "bowler_runs_calc"] = 0
    x.loc[bye, "batter_runs_calc"] = 0
    x.loc[bye, "batter_faced"] = 1
    x.loc[bye, "legal_ball"] = 1
    nb = ex.eq("overstep")
    nb_match = nb & e1.notna() & e2.notna() & runs.eq(e1 + e2)
    x.loc[nb_match, "team_runs_calc"] = e1[nb_match] + e2[nb_match]
    x.loc[nb_match, "batter_runs_calc"] = e2[nb_match]
    x.loc[nb_match, "bowler_runs_calc"] = e1[nb_match] + e2[nb_match]
    x.loc[nb_match, "batter_faced"] = 1
    x.loc[nb_match, "legal_ball"] = 0
    # Rows whose extras fields fail the supplied component reconciliation are unresolved.
    unknown = ~(known_normal | wide | bye | nb_match)
    valid.loc[unknown] = False
    x["attribution_status"] = np.where(valid, "RECONCILED", "UNRESOLVED_SOURCE_SEMANTICS")
    x["attribution_reason"] = "RECONCILED_SOURCE_RULE"
    x.loc[ex.eq("other"), "attribution_reason"] = "UNVALIDATED_OTHER_CATEGORY"
    x.loc[nb & ~nb_match, "attribution_reason"] = "NO_BALL_COMPONENTS_DO_NOT_RECONCILE"
    x.loc[~(known_normal | wide | bye | nb | ex.eq("other")), "attribution_reason"] = "UNMAPPED_EXTRAS_CATEGORY"
    x["team_wicket"] = x.is_wicket_b
    x["batter_dismissal"] = x.is_wicket_b & x.dismissed_player_id.fillna("").astype(str).ne("")
    x["bowler_credit_wicket"] = x.is_wicket_b & x.dismissal_type_id_n.isin([1, 2, 3, 5])
    x["batter_dot"] = (x.batter_runs_calc.eq(0) & x.batter_faced.eq(1) & x.legal_ball.eq(1)).astype("Int64")
    x["bowler_dot"] = (x.bowler_runs_calc.eq(0) & x.legal_ball.eq(1)).astype("Int64")
    fours = pd.to_numeric(x["is_four"], errors="coerce").fillna(0) if "is_four" in x else pd.Series(0, index=x.index)
    sixes = pd.to_numeric(x["is_six"], errors="coerce").fillna(0) if "is_six" in x else pd.Series(0, index=x.index)
    x["boundary_balls"] = (fours.eq(1) | sixes.eq(1)).astype(int)
    x["boundary_runs"] = fours * 4 + sixes * 6
    return x


def reconstruct_states(x: pd.DataFrame, matches: pd.DataFrame, playing: pd.DataFrame):
    x = x.sort_values(["match_id", "innings_n", "sequence"], kind="stable").copy()
    # exact playing-XI identity/entry order; no name-based matching
    lineup = playing[["match_id", "team_id", "player_id", "batting_order"]].copy()
    lineup["batting_order"] = pd.to_numeric(lineup.batting_order, errors="coerce")
    x = x.merge(lineup.rename(columns={"team_id": "lineup_team_id", "player_id": "striker_id", "batting_order": "striker_order"}),
                left_on=["match_id", "batting_team_id", "striker_id"], right_on=["match_id", "lineup_team_id", "striker_id"], how="left", validate="many_to_one")
    x = x.merge(lineup.rename(columns={"team_id": "lineup_team_id_b", "player_id": "non_striker_id", "batting_order": "non_striker_order"}),
                left_on=["match_id", "batting_team_id", "non_striker_id"], right_on=["match_id", "lineup_team_id_b", "non_striker_id"], how="left", validate="many_to_one")
    mm = matches.set_index("match_id")
    revised = mm.revised_target.fillna("").astype(str).str.strip().ne("")
    revised_context = revised.copy()
    for col in ("first_inn_revised_overs", "second_inn_revised_overs"):
        if col in mm:
            revised_context |= mm[col].fillna("").astype(str).str.strip().ne("")
    # Match-by-innings strict before/after states. Any unattributed run breaks score confidence for the rest of that innings.
    states = []
    season_benchmark = {}
    for season, sg in x[x.innings_n == 1].groupby("season"):
        complete_ids = [mid for mid, inn_rows in sg.groupby("match_id") if inn_rows.attribution_status.eq("RECONCILED").all()]
        good = sg[sg.match_id.isin(complete_ids)]
        season_benchmark[season] = float(good.team_runs_calc.sum() * 6 / max(1, int(good.legal_ball.fillna(0).sum()))) if len(good) else np.nan
    for (mid, inn), g in x.groupby(["match_id", "innings_n"], sort=False):
        score, legal, wickets, partner_runs, partner_balls = 0, 0, 0, 0, 0
        score_known = True
        recent_wicket_positions = []
        target = None
        if inn == 2 and mid in mm.index:
            if not revised_context.loc[mid]:
                first = x[(x.match_id == mid) & (x.innings_n == 1)]
                if first.attribution_status.eq("RECONCILED").all() and first.team_runs_calc.notna().all():
                    target = int(first.team_runs_calc.sum()) + 1
        for idx, row in g.iterrows():
            legal_cap = 120
            if mid in mm.index:
                cap_field = "first_inn_revised_overs" if inn == 1 else "second_inn_revised_overs"
                ov = pd.to_numeric(mm.loc[mid, cap_field], errors="coerce")
                if pd.notna(ov) and ov > 0:
                    legal_cap = int(ov * 6)
            phase = "PowerPlay" if legal < 36 else ("Death" if legal_cap - legal <= 30 else "Middle")
            rrr = ((target - score) * 6 / (legal_cap - legal)) if target is not None and inn == 2 and legal_cap > legal else np.nan
            sr = score * 6 / legal if legal else np.nan
            bench = season_benchmark.get(row.season, np.nan)
            first_pressure = (legal <= 90 and ((legal < 60 and wickets >= 4) or (legal >= 60 and wickets >= 6)))
            chase_pressure = inn == 2 and pd.notna(rrr) and rrr >= bench and (10 - wickets) <= 8
            pressure = bool(first_pressure or chase_pressure) if score_known else False
            before = {
                "score_before": score if score_known else np.nan, "wickets_before": wickets,
                "wickets_remaining": max(0, 10 - wickets), "legal_balls_before": legal,
                "legal_balls_remaining": max(0, legal_cap - legal), "overs_remaining": max(0, legal_cap - legal) / 6,
                "current_run_rate": sr, "target": target if inn == 2 else np.nan,
                "runs_required": target - score if target is not None and inn == 2 and score_known else np.nan,
                "required_run_rate": rrr, "phase": phase, "partnership_runs": partner_runs,
                "partnership_balls": partner_balls,
                "recent_wickets_12_legal_balls": sum(legal - p <= 12 for p in recent_wicket_positions),
                # Pre-state validity depends only on earlier deliveries, never the current outcome.
                "pressure": pressure, "state_status": "RECONSTRUCTED" if score_known else "PARTIAL_OR_UNRESOLVED",
                "target_status": "NOT_APPLICABLE" if inn == 1 else ("REVISED_TARGET_EFFECTIVE_TIME_UNVERIFIED" if revised_context.loc[mid] else ("NORMAL_TARGET_FROM_PRIOR_INNINGS" if target is not None else "FIRST_INNINGS_TOTAL_UNAVAILABLE")),
                "season_benchmark_run_rate": bench,
            }
            attr_ok = row.attribution_status == "RECONCILED"
            post = dict(before)
            if attr_ok:
                score += int(row.team_runs_calc)
                wickets += int(row.team_wicket)
                legal += int(row.legal_ball)
                partner_runs += int(row.team_runs_calc)
                partner_balls += int(row.legal_ball)
                if row.team_wicket:
                    recent_wicket_positions.append(legal)
                    partner_runs, partner_balls = 0, 0
            else:
                score_known = False
            post.update({"score_after": score if score_known else np.nan, "wickets_after": wickets,
                         "legal_balls_after": legal, "delivery_team_runs": row.team_runs_calc,
                         "delivery_batter_runs": row.batter_runs_calc, "delivery_bowler_runs": row.bowler_runs_calc,
                         "delivery_outcome_wicket": bool(row.team_wicket), "delivery_legal": row.legal_ball})
            states.append((idx, before, post))
    before_df = pd.DataFrame({i: b for i, b, _ in states}).T
    after_df = pd.DataFrame({i: a for i, _, a in states}).T
    for c in before_df.columns: x[c] = before_df[c].reindex(x.index)
    for c in after_df.columns: x[c] = after_df[c].reindex(x.index)
    # Recent wicket state and pressure movement always derive from pre-delivery context.
    return x


def classify_scenarios(x: pd.DataFrame) -> pd.DataFrame:
    x = x.sort_values(["match_id", "innings_n", "sequence"], kind="stable").copy()
    recent = pd.to_numeric(x.recent_wickets_12_legal_balls, errors="coerce").fillna(0)
    pp = x.legal_balls_before < 36
    middle = x.legal_balls_before.between(36, 89)
    death = x.legal_balls_remaining <= 30
    valid = x.state_status.eq("RECONSTRUCTED")
    x["B1"] = valid & pp & (x.wickets_before >= 2)
    x["B2"] = valid & middle
    x["B3"] = valid & death & (x.wickets_remaining >= 5)
    x["B4"] = valid & death & (recent >= 2)
    x["B5"] = valid & x.innings_n.eq(2) & x.required_run_rate.ge(x.season_benchmark_run_rate) & (x.wickets_remaining <= 5)
    x["B6"] = x.B5
    x["B6_resource_band"] = np.select([x.B5 & x.wickets_remaining.between(1,3), x.B5 & x.wickets_remaining.between(4,5)], ["1-3 wickets remaining", "4-5 wickets remaining"], default="OUTSIDE B6")
    x["B7"] = valid & x.striker_order.le(3) & x.non_striker_order.ge(6)
    x["B8"] = valid & (recent >= 1)
    x["B9"] = valid & death
    x["B10"] = False
    x["W1"] = valid & pp
    x["W2"] = valid & x.bowler_credit_wicket & x.partnership_runs.ge(20)
    x["W3"] = valid & death
    x["W4"] = valid & x.innings_n.eq(2) & pp
    x["W5"] = valid & x.innings_n.eq(2) & middle
    x["W6"] = valid & x.innings_n.eq(2) & death
    # B10 captures pressure transitions from adjacent pre-delivery states in strict sequence.
    prior = x.groupby(["match_id", "innings_n"], sort=False).pressure.shift(1)
    x["B10"] = valid & prior.notna() & x.pressure.ne(prior)
    pressure_flag = x.pressure.astype("boolean").fillna(False).astype(bool)
    prior_flag = prior.eq(True)
    x["pressure_change"] = np.select([pressure_flag & prior.eq(False), ~pressure_flag & prior_flag], ["INCREASE", "REDUCTION"], default="NO_CHANGE_OR_FIRST")
    # Pressure flags are discipline-specific, even where scenario evidence overlaps.
    x["batting_pressure"] = valid & x.pressure
    x["bowling_pressure"] = valid & x.pressure
    x["state_before_json"] = x[["score_before", "wickets_before", "wickets_remaining", "legal_balls_remaining", "current_run_rate", "target", "runs_required", "required_run_rate", "phase", "partnership_runs", "state_status"]].astype(object).where(pd.notna(x[["score_before", "wickets_before", "wickets_remaining", "legal_balls_remaining", "current_run_rate", "target", "runs_required", "required_run_rate", "phase", "partnership_runs", "state_status"]]), None).to_dict("records")
    x["delivery_ref"] = x.match_id.astype(str) + ":" + x.innings.astype(str) + ":" + x.innings_ball_num.astype(str)
    return x


def prior_baselines(x: pd.DataFrame) -> pd.DataFrame:
    """Strictly earlier delivery observations; same-player cumulative values shifted one event."""
    y = x.copy()
    y["event_time"] = pd.to_datetime(y.delivery_ist_time, errors="coerce", utc=True)
    y = y.sort_values(["event_time", "match_id", "innings_n", "sequence"], kind="stable")
    for idcol, value, exposure, prefix in [
        ("striker_id", "delivery_batter_runs", "batter_faced", "bat"),
        ("bowler_id", "delivery_bowler_runs", "legal_ball", "bowl"),
    ]:
        good = y[value].notna() & y[exposure].notna() & y[idcol].notna()
        v = pd.to_numeric(y[value], errors="coerce").where(good, 0)
        e = pd.to_numeric(y[exposure], errors="coerce").where(good, 0)
        cum_v = v.groupby(y[idcol]).cumsum().groupby(y[idcol]).shift(1).fillna(0)
        cum_e = e.groupby(y[idcol]).cumsum().groupby(y[idcol]).shift(1).fillna(0)
        y[f"{prefix}_prior_value"] = cum_v
        y[f"{prefix}_prior_exposure"] = cum_e
        y[f"{prefix}_prior_rate"] = (cum_v / cum_e.replace(0, np.nan))
        y[f"{prefix}_baseline_status"] = np.where(cum_e.gt(0), "PRIOR_ONLY_AVAILABLE", "INSUFFICIENT_PRIOR_HISTORY")
    return y.sort_index()


def _group_summary(x: pd.DataFrame, key: str, discipline: str) -> pd.DataFrame:
    if discipline == "batting":
        x = x.copy()
        prior_ok = x.bat_baseline_status.eq("PRIOR_ONLY_AVAILABLE")
        x["bat_baseline_runs"] = x.delivery_batter_runs.where(prior_ok)
        g = x[x[key] & x.delivery_batter_runs.notna() & x.batter_faced.eq(1)].groupby(["striker_id", "striker_name"])
        z = g.agg(opportunities=("delivery_ref", "count"), pressure_runs=("delivery_batter_runs", "sum"),
                  matches=("match_id", "nunique"), seasons=("season", "nunique"), dots=("batter_dot", "sum"),
                  boundary_runs=("boundary_runs", "sum"), boundary_balls=("boundary_balls", "sum"),
                  dismissals=("batter_dismissal", "sum"),
                  baseline_pressure_runs=("bat_baseline_runs", "sum"),
                  prior_expected=("bat_prior_rate", "sum"), baseline_events=("bat_baseline_status", lambda s: s.eq("PRIOR_ONLY_AVAILABLE").sum()),
                  prior_balls=("bat_prior_exposure", "sum")).reset_index()
        z["effectiveness"] = z.pressure_runs / z.opportunities * 100
        z["pressure_strike_rate"] = z.effectiveness
        z["baseline_strike_rate"] = z.prior_expected / z.baseline_events.replace(0, np.nan) * 100
        z["delta_vs_prior"] = (z.baseline_pressure_runs - z.prior_expected) / z.baseline_events.replace(0, np.nan) * 100
        z["dot_pct"] = z.dots / z.opportunities * 100
        z["boundary_pct"] = z.boundary_balls / z.opportunities * 100
        z["dismissal_frequency"] = z.dismissals / z.opportunities
        coverage = x[x[key]].groupby("striker_id")[[f"B{i}" for i in range(1, 11)]].any().sum(axis=1)
        z["player_id"] = z.striker_id
    else:
        x = x.copy()
        prior_ok = x.bowl_baseline_status.eq("PRIOR_ONLY_AVAILABLE")
        x["bowl_baseline_runs"] = (x.bowl_prior_rate * x.legal_ball).where(prior_ok & x.legal_ball.eq(1))
        g = x[x[key] & x.delivery_bowler_runs.notna()].groupby(["bowler_id", "bowler_name"])
        z = g.agg(pressure_deliveries=("delivery_ref", "count"), conceded=("delivery_bowler_runs", "sum"), legal_balls=("legal_ball", "sum"), wickets=("bowler_credit_wicket", "sum"),
                  matches=("match_id", "nunique"), seasons=("season", "nunique"), dots=("bowler_dot", "sum"),
                  boundaries_conceded=("boundary_balls", "sum"),
                  baseline_pressure_runs=("bowl_baseline_runs", "sum"),
                  prior_expected=("bowl_baseline_runs", "sum"), baseline_events=("bowl_baseline_runs", "count"),
                  prior_balls=("bowl_prior_exposure", "sum")).reset_index()
        z["opportunities"] = z.legal_balls
        z["effectiveness"] = z.conceded / z.legal_balls.replace(0, np.nan) * 6
        z["pressure_economy"] = z.effectiveness
        z["baseline_economy"] = z.prior_expected / z.baseline_events.replace(0, np.nan) * 6
        z["delta_vs_prior"] = (z.prior_expected - z.conceded) / z.legal_balls.replace(0, np.nan) * 6
        z["wicket_rate"] = z.wickets / z.legal_balls.replace(0, np.nan) * 6
        z["dot_pct"] = z.dots / z.legal_balls.replace(0, np.nan) * 100
        coverage = x[x[key]].groupby("bowler_id")[[f"W{i}" for i in range(1, 7)]].any().sum(axis=1)
        z["player_id"] = z.bowler_id
    z["scenario_coverage"] = z.player_id.map(coverage).fillna(0).astype(int)
    if discipline == "batting":
        z["pressure_deliveries"] = z.opportunities
    z["reliability"] = np.select([z.matches.ge(10) & z.opportunities.ge(60), z.matches.ge(5) & z.opportunities.ge(30)], ["HIGHER_COVERAGE", "MODERATE_COVERAGE"], default="LOW_COVERAGE")
    z["eligibility_status"] = np.where(z.matches.ge(5) & z.opportunities.ge(30) & z.baseline_events.gt(0), "PROVISIONALLY_ELIGIBLE", "INSUFFICIENT_EVIDENCE")
    z["consistency"] = "MATCH AND SEASON DISPERSION SHOWN; not uncertainty"
    # Descriptive repeatability across player-match and player-season pressure outcomes.
    if discipline == "batting":
        eligible_events = x[x[key] & x.delivery_batter_runs.notna() & x.batter_faced.eq(1)]
        by_match = eligible_events.groupby(["striker_id", "match_id"]).agg(v=("delivery_batter_runs", "sum"), e=("batter_faced", "sum"))
        by_season = eligible_events.groupby(["striker_id", "season"]).agg(v=("delivery_batter_runs", "sum"), e=("batter_faced", "sum"))
        scale = 100
    else:
        eligible_events = x[x[key] & x.delivery_bowler_runs.notna()]
        by_match = eligible_events.groupby(["bowler_id", "match_id"]).agg(v=("delivery_bowler_runs", "sum"), e=("legal_ball", "sum"))
        by_season = eligible_events.groupby(["bowler_id", "season"]).agg(v=("delivery_bowler_runs", "sum"), e=("legal_ball", "sum"))
        scale = 6
    by_match["rate"] = by_match.v / by_match.e.replace(0, np.nan) * scale
    by_season["rate"] = by_season.v / by_season.e.replace(0, np.nan) * scale
    idx = z.player_id
    mcol = "striker_id" if discipline == "batting" else "bowler_id"
    z["pressure_matches"] = z.matches
    z["match_level_consistency_sd"] = idx.map(by_match.groupby(level=0).rate.std())
    z["season_level_consistency_sd"] = idx.map(by_season.groupby(level=0).rate.std())
    z["consistency_status"] = np.where(z.matches.ge(2), "DESCRIPTIVE_SD_AVAILABLE", "INSUFFICIENT_REPEAT_MATCHES")
    z["pressure_definition"] = "provisional-v0.1"
    return z


def _rank(table: pd.DataFrame, discipline: str, floor_matches=5, floor_opportunities=30):
    z = table.copy()
    z["eligibility_status"] = np.where(z.matches.ge(floor_matches) & z.opportunities.ge(floor_opportunities) & z.baseline_events.gt(0), "PROVISIONALLY_ELIGIBLE", "INSUFFICIENT_EVIDENCE")
    eligible = z[z.eligibility_status == "PROVISIONALLY_ELIGIBLE"].copy()
    # No composite score: order pressure improvement over a prior-only per-delivery baseline,
    # then coverage, then discipline outcome as transparent deterministic tie-breaks.
    if discipline == "batting":
        cols = ["delta_vs_prior", "scenario_coverage", "matches", "pressure_strike_rate"]
        asc = [False, False, False, False]
    else:
        cols = ["delta_vs_prior", "scenario_coverage", "matches", "wicket_rate"]
        asc = [False, False, False, False]
    eligible = eligible.sort_values(cols + ["player_id"], ascending=asc + [True], kind="stable")
    eligible.insert(0, "rank", range(1, len(eligible) + 1))
    return eligible


def build_product(write=True):
    integrity, comps, matches, d, playing, mapping, teams, dup_exact, dup_key, source_match_count, source_delivery_count = load_population()
    attributed = _attribute(d)
    x = reconstruct_states(attributed, matches, playing)
    x = classify_scenarios(x)
    x = prior_baselines(x)
    # Match identities are exact IDs only; unresolved numeric identifiers remain visible.
    player_map = mapping.drop_duplicates(["player_id", "player_name"]).drop_duplicates("player_id").set_index("player_id").player_name
    x["striker_name"] = x.striker_id.map(player_map).fillna(x.striker_name)
    x["bowler_name"] = x.bowler_id.map(player_map).fillna(x.bowler_name)
    bat = _group_summary(x, "batting_pressure", "batting")
    bowl = _group_summary(x, "bowling_pressure", "bowling")
    bat_rank = _rank(bat, "batting")
    bowl_rank = _rank(bowl, "bowling")
    bat_scenarios, bowl_scenarios = [], []
    for i in range(1, 11):
        if i == 6:
            for band in ("1-3 wickets remaining", "4-5 wickets remaining"):
                s = _group_summary(x[x.B6_resource_band.eq(band)], "B6", "batting")
                if not s.empty:
                    s.insert(0, "scenario", "B6")
                    s.insert(1, "resource_band", band)
                bat_scenarios.append(s)
        else:
            s = _group_summary(x, f"B{i}", "batting")
            if not s.empty: s.insert(0, "scenario", f"B{i}")
            bat_scenarios.append(s)
    for i in range(1, 7):
        s = _group_summary(x, f"W{i}", "bowling")
        if not s.empty: s.insert(0, "scenario", f"W{i}")
        bowl_scenarios.append(s)
    bat_scenario = pd.concat(bat_scenarios, ignore_index=True) if bat_scenarios else pd.DataFrame()
    bowl_scenario = pd.concat(bowl_scenarios, ignore_index=True) if bowl_scenarios else pd.DataFrame()
    # Sensitivity over plausible minimum coverage floors and seasonal pressure alternatives.
    sensitivity = []
    base_top = {}
    base_rank_map = {}
    for discipline, table in [("batting", bat), ("bowling", bowl)]:
        primary_ranks = _rank(table, discipline)
        base_top[discipline] = primary_ranks.player_id.astype(str).head(10).tolist()
        base_rank_map[discipline] = dict(zip(primary_ranks.player_id.astype(str), primary_ranks["rank"].astype(int)))
        for m, n in [(3, 15), (5, 30), (10, 60)]:
            ranks = _rank(table, discipline, m, n)
            motion = [{"player_id": str(row.player_id), "primary_rank": base_rank_map[discipline].get(str(row.player_id)), "variant_rank": int(row["rank"])} for _, row in ranks.head(10).iterrows()]
            sensitivity.append({"discipline": discipline, "variant": f"coverage_{m}matches_{n}opps", "eligible": len(ranks),
                                "top10_ids": ",".join(ranks.player_id.astype(str).head(10)), "top10_names": " | ".join(ranks.iloc[:, 2].astype(str).head(10)) if len(ranks) else "",
                                "overlap_with_primary": len(set(base_top[discipline]) & set(ranks.player_id.astype(str).head(10))), "rank_movement_top10": json.dumps(motion)})
    # Pressure-boundary alternatives use the same outcome attribution and prior-only baselines.
    for label, multiplier, wickets_left, early, late in [("pressure_loose", 0.9, 8, 3, 5), ("pressure_primary", 1.0, 8, 4, 6), ("pressure_strict", 1.25, 6, 5, 7)]:
        alt = x.copy()
        first_alt = ((alt.legal_balls_before < 60) & (alt.wickets_before >= early)) | ((alt.legal_balls_before >= 60) & (alt.legal_balls_before < 90) & (alt.wickets_before >= late))
        chase_alt = alt.innings_n.eq(2) & alt.required_run_rate.ge(alt.season_benchmark_run_rate * multiplier) & alt.wickets_remaining.le(wickets_left)
        alt["batting_pressure"] = alt.state_status.eq("RECONSTRUCTED") & (first_alt | chase_alt)
        alt["bowling_pressure"] = alt["batting_pressure"]
        for discipline in ("batting", "bowling"):
            table = _group_summary(alt, f"{discipline}_pressure", discipline)
            ranks = _rank(table, discipline)
            ids = ranks.player_id.astype(str).head(10).tolist()
            motion = [{"player_id": str(row.player_id), "primary_rank": base_rank_map[discipline].get(str(row.player_id)), "variant_rank": int(row["rank"])} for _, row in ranks.head(10).iterrows()]
            sensitivity.append({"discipline": discipline, "variant": label, "eligible": len(ranks), "top10_ids": ",".join(ids),
                                "top10_names": " | ".join(ranks.iloc[:, 2].astype(str).head(10)) if len(ranks) else "",
                                "overlap_with_primary": len(set(base_top[discipline]) & set(ids)), "rank_movement_top10": json.dumps(motion)})
    # Leave-one-season-out ranking stability. All baseline events remain strictly prior-only.
    for season in SEASONS:
        remaining = x[x.season.ne(season)]
        for discipline in ("batting", "bowling"):
            table = _group_summary(remaining, f"{discipline}_pressure", discipline)
            ranks = _rank(table, discipline)
            ids = ranks.player_id.astype(str).head(10).tolist()
            motion = [{"player_id": str(row.player_id), "primary_rank": base_rank_map[discipline].get(str(row.player_id)), "variant_rank": int(row["rank"])} for _, row in ranks.head(10).iterrows()]
            sensitivity.append({"discipline": discipline, "variant": f"leave_out_{season}", "eligible": len(ranks), "top10_ids": ",".join(ids),
                                "top10_names": " | ".join(ranks.iloc[:, 2].astype(str).head(10)) if len(ranks) else "",
                                "overlap_with_primary": len(set(base_top[discipline]) & set(ids)), "rank_movement_top10": json.dumps(motion)})
    # Population and all exclusions are generated from the same filtered source run.
    per_season_match = matches.groupby("season").match_id.nunique().to_dict()
    per_season_deliveries = d.groupby("season").size().to_dict()
    sequence = d.groupby(["match_id", "innings"], sort=False).sequence
    invalid_sequence_mask = d.sequence.isna() | d.sequence.le(0) | sequence.diff().le(0).fillna(False)
    unresolved_ids = set()
    known_keys = set(zip(mapping.comp_id.astype(str), mapping.player_id.astype(str)))
    for idcol in ("striker_id", "bowler_id"):
        unresolved_ids |= {(str(c), str(p)) for c, p in zip(d.comp_id, d[idcol]) if pd.notna(p) and (str(c), str(p)) not in known_keys}
    quality = [
        {"item": "archive_sha256", "value": integrity["archive_sha256"], "status": "VERIFIED"},
        {"item": "excluded_non_ipl_match_records", "value": source_match_count - int(matches.match_id.nunique()), "status": "EXACT_COMPETITION_ID_FILTER"},
        {"item": "excluded_non_ipl_delivery_records", "value": source_delivery_count - len(d), "status": "EXACT_COMPETITION_ID_FILTER"},
        {"item": "matches_by_season", "value": json.dumps({str(k): int(v) for k,v in per_season_match.items()}, sort_keys=True), "status": "SOURCE_POPULATION"},
        {"item": "deliveries_by_season", "value": json.dumps({str(k): int(v) for k,v in per_season_deliveries.items()}, sort_keys=True), "status": "SOURCE_POPULATION"},
        {"item": "unique_player_ids", "value": int(pd.concat([d.striker_id, d.bowler_id]).nunique()), "status": "SOURCE_POPULATION"},
        {"item": "unique_teams", "value": int(pd.concat([d.batting_team_id, d.bowling_team_id]).nunique()), "status": "SOURCE_POPULATION"},
        {"item": "missing_match_id", "value": int(d.match_id.isna().sum()), "status": "SOURCE_AUDIT"},
        {"item": "missing_innings", "value": int(d.innings.isna().sum()), "status": "SOURCE_AUDIT"},
        {"item": "missing_batter_id", "value": int(d.striker_id.isna().sum()), "status": "SOURCE_AUDIT"},
        {"item": "missing_bowler_id", "value": int(d.bowler_id.isna().sum()), "status": "SOURCE_AUDIT"},
        {"item": "duplicate_delivery_rows", "value": dup_exact, "status": "SOURCE_AUDIT"},
        {"item": "duplicate_match_innings_sequence", "value": dup_key, "status": "SOURCE_AUDIT"},
        {"item": "invalid_delivery_sequence_records", "value": int(invalid_sequence_mask.sum()), "status": "SOURCE_AUDIT"},
        {"item": "unresolved_extras_or_run_semantics", "value": int(x.attribution_status.ne("RECONCILED").sum()), "status": "EXCLUDED_FROM_STATE"},
        {"item": "extras_rows_by_reason", "value": json.dumps({f"{a}|{b}": int(n) for (a,b),n in x.groupby(["extras_type", "attribution_reason"], dropna=False).size().items()}, sort_keys=True), "status": "SOURCE_RECONCILIATION"},
        {"item": "runs_total_interpretation_validation", "value": json.dumps({"wide_rows_with_runs_zero_and_extras_positive": int((x.extras_type.eq("wide") & x.runs_n.eq(0) & x.extras1_runs_n.gt(0)).sum()), "byes_legbyes_rows_with_runs_zero_and_extras_positive": int((x.extras_type.isin(["byes", "legbyes"]) & x.runs_n.eq(0) & x.extras1_runs_n.gt(0)).sum()), "overstep_rows_not_equal_components": int((x.extras_type.eq("Overstep") & x.runs_n.ne(x.extras1_runs_n + x.extras_2_runs_n)).sum())}, sort_keys=True), "status": "CONFLICTS_WITH_SUPPLIED_INTERPRETATION"},
        {"item": "innings_pre_state_complete", "value": int(x.groupby(["match_id", "innings_n"]).state_status.apply(lambda s: s.eq("RECONSTRUCTED").all()).sum()), "status": "PRE_DELIVERY_STATE_COVERAGE"},
        {"item": "innings_with_all_outcomes_reconciled", "value": int(x.groupby(["match_id", "innings_n"]).attribution_status.apply(lambda s: s.eq("RECONCILED").all()).sum()), "status": "POST_DELIVERY_STATE_COVERAGE"},
        {"item": "innings_with_partial_outcome_data", "value": int(x.groupby(["match_id", "innings_n"]).attribution_status.apply(lambda s: s.ne("RECONCILED").any()).sum()), "status": "POST_DELIVERY_STATE_COVERAGE"},
        {"item": "unresolved_player_competition_id_pairs", "value": len(unresolved_ids), "status": "EXACT_ID_JOIN_ONLY"},
        {"item": "unsupported_dismissal_ids", "value": json.dumps(x.loc[x.is_wicket_b & ~x.dismissal_type_id_n.isin([1,2,3,4,5]), "dismissal_type_id"].value_counts().to_dict()), "status": "EXPLICITLY_UNMAPPED"},
        {"item": "pressure_deliveries", "value": int(x.batting_pressure.sum()), "status": "PROVISIONAL_CLASSIFICATION"},
        {"item": "pressure_baseline_timestamp_coverage", "value": int(x.event_time.notna().sum()), "status": "PRIOR_ONLY_BASELINES"},
    ]
    sensitivity_df = pd.DataFrame(sensitivity)
    # Evidence traces preserve the source row key and full pre-state/outcome for each classified delivery.
    trace_cols = ["delivery_ref", "match_id", "innings", "innings_ball_num", "season", "striker_id", "striker_name", "bowler_id", "bowler_name", "batting_team_id", "bowling_team_id", "score_before", "wickets_before", "wickets_remaining", "legal_balls_remaining", "current_run_rate", "target", "runs_required", "required_run_rate", "phase", "partnership_runs", "partnership_balls", "pressure", "state_status", "target_status", "attribution_status", "attribution_reason", "delivery_team_runs", "delivery_batter_runs", "delivery_bowler_runs", "delivery_outcome_wicket", "delivery_legal", "score_after", "wickets_after", "legal_balls_after", "pressure_change"] + [f"B{i}" for i in range(1,11)] + [f"W{i}" for i in range(1,7)]
    traces = x[trace_cols].copy()
    baselines = pd.concat([
        x.groupby(["striker_id", "striker_name"], dropna=False).agg(events=("delivery_ref", "count"), prior_baseline_coverage=("bat_baseline_status", lambda s:s.eq("PRIOR_ONLY_AVAILABLE").sum()), prior_batter_runs=("bat_prior_value", "sum"), prior_balls=("bat_prior_exposure", "sum")).reset_index().rename(columns={"striker_id":"player_id", "striker_name":"player_name"}).assign(discipline="batting"),
        x.groupby(["bowler_id", "bowler_name"], dropna=False).agg(events=("delivery_ref", "count"), prior_baseline_coverage=("bowl_baseline_status", lambda s:s.eq("PRIOR_ONLY_AVAILABLE").sum()), prior_batter_runs=("bowl_prior_value", "sum"), prior_balls=("bowl_prior_exposure", "sum")).reset_index().rename(columns={"bowler_id":"player_id", "bowler_name":"player_name"}).assign(discipline="bowling"),
    ], ignore_index=True)
    consistency = pd.concat([bat.assign(discipline="batting"), bowl.assign(discipline="bowling")], ignore_index=True)
    reliability_cols = [c for c in ["player_id", "discipline", "opportunities", "pressure_deliveries", "legal_balls", "matches", "seasons", "scenario_coverage", "reliability", "eligibility_status"] if c in consistency]
    reliability = consistency[reliability_cols].copy()
    explanations = {
        "data_version": DATA_VERSION, "methodology_version": METHODOLOGY_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "population": "IPL seasons 2022-2026 exact competition identifiers",
        "batter_status": "PROVISIONAL observational ordering; read the limitations in methodology_configuration.json",
        "bowler_status": "PROVISIONAL observational ordering; read the limitations in methodology_configuration.json",
        "batters": bat_rank.head(10).replace({np.nan: None}).to_dict("records"),
        "bowlers": bowl_rank.head(10).replace({np.nan: None}).to_dict("records"),
        "next_batters": bat_rank.iloc[10:15].replace({np.nan: None}).to_dict("records"),
        "next_bowlers": bowl_rank.iloc[10:15].replace({np.nan: None}).to_dict("records"),
        "ranking_note": "Ordered by pressure improvement over the player's pre-event IPL delivery baseline; scenario coverage and match counts are tie-breakers. No arbitrary composite score is used. Coverage floor and tie policy are provisional research recommendations, not approval.",
    }
    for label, rank_table, event_col, pressure_col, baseline_col, scenario_table in [
        ("batters", bat_rank, "striker_id", "batting_pressure", "batting_scenarios", bat_scenario),
        ("bowlers", bowl_rank, "bowler_id", "bowling_pressure", "bowling_scenarios", bowl_scenario),
    ]:
        rows = []
        for pos, (_, player) in enumerate(rank_table.head(10).iterrows()):
            pid = str(player.player_id)
            p_events = x[(x[event_col].astype(str) == pid) & x[pressure_col] & x.delivery_ref.notna()]
            scenario_rows = scenario_table[scenario_table.player_id.astype(str).eq(pid)]
            scenario_rows = scenario_rows.sort_values("delta_vs_prior", ascending=False) if not scenario_rows.empty else scenario_rows
            refs = p_events.delivery_ref.astype(str).head(30).tolist()
            base = player.to_dict()
            base["evidence_delivery_refs_sample"] = refs
            base["best_scenarios_by_prior_contrast"] = scenario_rows.head(3).scenario.tolist() if not scenario_rows.empty else []
            base["weakest_scenarios_by_prior_contrast"] = scenario_rows.tail(3).sort_values("delta_vs_prior").scenario.tolist() if not scenario_rows.empty else []
            next_player = rank_table.iloc[pos + 1] if pos + 1 < min(10, len(rank_table)) else None
            next_clause = f" Next is {next_player.get('striker_name' if discipline == 'batting' else 'bowler_name')} at {next_player.get('delta_vs_prior', np.nan):.2f}." if next_player is not None else " This is the final eligible position."
            base["why_ranked_here"] = f"Prior-only pressure contrast {player.get('delta_vs_prior', np.nan):.2f}; ordered by that dimension, with scenario coverage and distinct matches as tie-breakers.{next_clause}"
            base["limitations"] = "Provisional pressure definition and eligibility floor; descriptive raw comparison; no role adjustment or clustered uncertainty interval."
            rows.append(base)
        explanations[label] = rows
    result = {"data_version": DATA_VERSION, "methodology_version": METHODOLOGY_VERSION, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "competitions": comps, "matches": matches, "deliveries": x, "batters": bat, "bowlers": bowl, "bat_rankings": bat_rank, "bowl_rankings": bowl_rank,
              "batting_scenarios": bat_scenario, "bowling_scenarios": bowl_scenario, "baselines": baselines, "consistency": consistency,
              "reliability": reliability, "traces": traces, "quality": pd.DataFrame(quality), "sensitivity": sensitivity_df, "explanations": explanations}
    if write:
        write_exports(result)
    return result


def write_exports(r):
    OUT.mkdir(parents=True, exist_ok=True)
    outputs = {
        "top_10_pressure_batters.csv": r["bat_rankings"].head(10), "top_10_pressure_bowlers.csv": r["bowl_rankings"].head(10),
        "all_batter_rankings.csv": r["bat_rankings"], "all_bowler_rankings.csv": r["bowl_rankings"],
        "batting_scenario_metrics.csv": r["batting_scenarios"], "bowling_scenario_metrics.csv": r["bowling_scenarios"],
        "player_pressure_baselines.csv": r["baselines"], "player_consistency_metrics.csv": r["consistency"],
        "player_reliability_metrics.csv": r["reliability"], "pressure_delivery_classifications.csv": r["traces"],
        "data_quality_report.csv": r["quality"], "ranking_sensitivity_report.csv": r["sensitivity"],
    }
    definitions = {
        "top_10_pressure_batters.csv": "Top 10 provisional batting order; pressure runs per faced legal ball; prior-only pressure strike-rate difference; candidate floor 5 pressure matches and 30 faced balls.",
        "top_10_pressure_bowlers.csv": "Top 10 provisional bowling order; conceded runs include attributed wides/no-balls and economy uses legal balls; prior-only economy difference; candidate floor 5 pressure matches and 30 legal balls.",
        "all_batter_rankings.csv": "Same fields and ordering as provisional batting Top 10, across all candidates meeting the research floor.",
        "all_bowler_rankings.csv": "Same fields and ordering as provisional bowling Top 10, across all candidates meeting the research floor.",
        "batting_scenario_metrics.csv": "Scenario-specific batter opportunities and outcomes by player; B1-B10 membership is defined in methodology_configuration.json.",
        "bowling_scenario_metrics.csv": "Scenario-specific bowler opportunities and outcomes by player; W1-W6 membership is defined in methodology_configuration.json.",
        "player_pressure_baselines.csv": "Per-player prior-only cumulative baseline coverage and exposures; evaluated event excluded.",
        "player_consistency_metrics.csv": "Descriptive match and season outcome dispersion; not a confidence interval or uncertainty estimator.",
        "player_reliability_metrics.csv": "Coverage-based provisional reliability label, with separate delivery and legal-ball exposure where applicable.",
        "pressure_delivery_classifications.csv": "Delivery-level pre-state, outcome and post-state; scenario flags; composite source key is match_id:innings:innings_ball_num.",
        "data_quality_report.csv": "Population, source-integrity, attribution, sequence, identity and state-coverage audit counts.",
        "ranking_sensitivity_report.csv": "Eligibility-floor, pressure-definition and leave-one-season-out candidate rank stability.",
    }
    for name, frame in outputs.items():
        frame.assign(data_version=DATA_VERSION, methodology_version=METHODOLOGY_VERSION,
                     generated_at_utc=r["generated_at_utc"], population="IPL 2022-2026 exact competition IDs",
                     metric_definition=definitions[name]).to_csv(OUT / name, index=False)
    (OUT / "ranking_explanations.json").write_text(json.dumps(r["explanations"], indent=2, default=str), encoding="utf-8")
    config = dict(METHODOLOGY)
    config.update({"generated_at_utc": r["generated_at_utc"], "metric_definition": "Versioned provisional pressure classification, scenarios, population, and known limitations."})
    (OUT / "methodology_configuration.json").write_text(json.dumps(config, indent=2), encoding="utf-8")



