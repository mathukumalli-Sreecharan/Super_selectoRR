from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from services.pressure_product import METHODOLOGY, OUT, build_product

PAGES = (
    "Executive Overview", "Top 10 Pressure Batters", "Top 10 Pressure Bowlers",
    "Batting Pressure Analytics", "Bowling Pressure Analytics", "Scenario Explorer",
    "Player Deep Dive", "Match and Delivery Explorer", "Pressure vs Normal Comparison",
    "Consistency and Reliability", "Ranking Methodology", "Data Quality and Coverage",
    "Sensitivity Analysis", "Export Centre",
)


@st.cache_data(show_spinner="Validating the source archive and reconstructing IPL delivery states…")
def _analytics():
    return build_product(write=True)


def _download_frame(frame: pd.DataFrame, filename: str):
    st.download_button(f"Download {filename}", frame.to_csv(index=False).encode("utf-8"), filename, "text/csv")


def _top_page(r, discipline):
    bat = discipline == "batting"
    title = "Top 10 Pressure Batters" if bat else "Top 10 Pressure Bowlers"
    table = r["bat_rankings"] if bat else r["bowl_rankings"]
    st.subheader(title)
    st.caption("Provisional observational ordering from IPL delivery evidence. Method parameters are versioned, but the pressure definition and coverage floors have not been formally approved.")
    if table.empty:
        st.warning("No player met the provisional evidence floor. No positions are fabricated.")
        return
    st.dataframe(table.head(10), use_container_width=True, hide_index=True)
    st.markdown("**How this ordering works:** prior-only pressure improvement is the primary ordering dimension. Scenario coverage and distinct matches break ties. No cross-metric weighted score is used.")
    st.caption(f"Eligible players: {len(table)}. Next candidates are shown below when available.")
    if len(table) > 10:
        st.dataframe(table.iloc[10:15], use_container_width=True, hide_index=True)


def _scenario_explorer(r):
    discipline = st.radio("Discipline", ["Batting", "Bowling"], horizontal=True)
    scenarios = [f"B{i}" for i in range(1, 11)] if discipline == "Batting" else [f"W{i}" for i in range(1, 7)]
    scenario = st.selectbox("Scenario", scenarios)
    d = r["deliveries"]
    result = d[d[scenario].fillna(False)].copy()
    seasons = sorted(result.season.dropna().unique().tolist())
    selected_seasons = st.multiselect("Season", seasons, default=seasons)
    players = "striker_id" if discipline == "Batting" else "bowler_id"
    names = "striker_name" if discipline == "Batting" else "bowler_name"
    names_available = result[names].dropna().drop_duplicates().sort_values().tolist()
    selected_player = st.selectbox("Player (optional)", ["All"] + names_available)
    result = result[result.season.isin(selected_seasons)]
    if selected_player != "All": result = result[result[names] == selected_player]
    st.metric("Delivery exposures", f"{len(result):,}")
    cols = ["delivery_ref", "season", "striker_name", "bowler_name", "score_before", "wickets_before", "legal_balls_remaining", "required_run_rate", "phase", "delivery_batter_runs", "delivery_bowler_runs", "delivery_outcome_wicket", "state_status"]
    st.dataframe(result[cols].head(1000), use_container_width=True, hide_index=True)


def _player_deep_dive(r):
    discipline = st.radio("Discipline", ["Batter", "Bowler"], horizontal=True)
    table = r["bat_rankings"] if discipline == "Batter" else r["bowl_rankings"]
    idcol = "striker_id" if discipline == "Batter" else "bowler_id"
    namecol = "striker_name" if discipline == "Batter" else "bowler_name"
    choices = table[[idcol, namecol]].drop_duplicates().sort_values(namecol)
    if choices.empty:
        st.info("No eligible candidate to display.")
        return
    selected = st.selectbox("Player", choices.itertuples(index=False, name=None), format_func=lambda x: f"{x[1]} · ID {x[0]}")
    pid = selected[0]
    row = table[table[idcol].astype(str) == str(pid)]
    if not row.empty: st.dataframe(row, use_container_width=True, hide_index=True)
    scenarios = r["batting_scenarios"] if discipline == "Batter" else r["bowling_scenarios"]
    metric_id = "player_id"
    st.subheader("Scenario performance")
    st.dataframe(scenarios[scenarios[metric_id].astype(str) == str(pid)], use_container_width=True, hide_index=True)
    d = r["deliveries"]
    pcol = "striker_id" if discipline == "Batter" else "bowler_id"
    st.subheader("Delivery evidence")
    st.dataframe(d[d[pcol].astype(str) == str(pid)][["delivery_ref", "season", "score_before", "wickets_before", "required_run_rate", "phase", "pressure", "state_status", "delivery_batter_runs", "delivery_bowler_runs", "delivery_outcome_wicket"]].head(100), use_container_width=True, hide_index=True)


def render_dashboard(section: str) -> None:
    st.title(section)
    r = _analytics()
    qa = r["quality"].set_index("item")["value"].to_dict()
    if section == "Executive Overview":
        a, b, c, d = st.columns(4)
        a.metric("IPL matches", f"{r['matches'].match_id.nunique():,}")
        b.metric("IPL deliveries", f"{len(r['deliveries']):,}")
        c.metric("Seasons", "2022–2026")
        d.metric("Player IDs", str(qa["unique_player_ids"]))
        st.warning("The pressure model is provisional. Source reconciliation excludes unresolved delivery outcomes, and current rank orderings are descriptive research candidates.")
        st.write(f"Source population includes {qa['pressure_deliveries']:,} provisionally classified pressure deliveries, across {len(r['bat_rankings'])} batter and {len(r['bowl_rankings'])} bowler candidates meeting the current evidence floor.")
        st.subheader("Provisional pressure leaders")
        left, right = st.columns(2)
        left.dataframe(r["bat_rankings"].head(5), use_container_width=True, hide_index=True)
        right.dataframe(r["bowl_rankings"].head(5), use_container_width=True, hide_index=True)
        st.caption("Conventional runs and wickets leaderboards are not used as pressure rankings.")
    elif section == "Top 10 Pressure Batters": _top_page(r, "batting")
    elif section == "Top 10 Pressure Bowlers": _top_page(r, "bowling")
    elif section == "Batting Pressure Analytics":
        st.subheader("Batting pressure effectiveness and baseline comparison")
        st.dataframe(r["bat_rankings"], use_container_width=True, hide_index=True)
        st.caption("Effectiveness and pressure-vs-prior baseline difference are separate columns; opportunity counts and coverage are shown alongside them.")
    elif section == "Bowling Pressure Analytics":
        st.subheader("Bowling pressure effectiveness and baseline comparison")
        st.dataframe(r["bowl_rankings"], use_container_width=True, hide_index=True)
        st.caption("Economy suppression against the bowler's prior-only delivery baseline is separate from wickets per six legal balls.")
    elif section == "Scenario Explorer": _scenario_explorer(r)
    elif section == "Player Deep Dive": _player_deep_dive(r)
    elif section == "Match and Delivery Explorer":
        d = r["deliveries"]
        matches = sorted(d.match_id.astype(str).unique())
        mid = st.selectbox("Match ID", matches)
        inn = st.selectbox("Innings", sorted(d[d.match_id.astype(str) == mid].innings.astype(str).unique()))
        cols = ["delivery_ref", "striker_name", "non_striker_name", "bowler_name", "score_before", "wickets_before", "wickets_remaining", "legal_balls_remaining", "current_run_rate", "target", "runs_required", "required_run_rate", "phase", "partnership_runs", "pressure", "state_status", "delivery_batter_runs", "delivery_bowler_runs", "delivery_outcome_wicket"]
        st.dataframe(d[(d.match_id.astype(str) == mid) & (d.innings.astype(str) == inn)][cols], use_container_width=True, hide_index=True)
    elif section == "Pressure vs Normal Comparison":
        st.subheader("Pressure and non-pressure delivery summaries")
        for discipline, table in [("Batting", r["batters"]), ("Bowling", r["bowlers"])]:
            st.markdown(f"**{discipline}**")
            st.dataframe(table, use_container_width=True, hide_index=True)
        st.caption("The baseline is built from earlier IPL delivery events only. It is not adjusted for role, phase, opponent, or match context.")
    elif section == "Consistency and Reliability":
        st.caption("Reliability is an opportunity and coverage label under provisional floors. Match-clustered consistency and uncertainty intervals are not estimated yet.")
        st.dataframe(r["reliability"], use_container_width=True, hide_index=True)
    elif section == "Ranking Methodology":
        st.warning("Research recommendation; not formally adopted. Scores are not causal estimates and do not use an arbitrary composite.")
        st.json(METHODOLOGY)
    elif section == "Data Quality and Coverage":
        st.dataframe(r["quality"], use_container_width=True, hide_index=True)
        st.subheader("Extras category reconciliation")
        st.dataframe(r["deliveries"].groupby(["extras_type", "attribution_status"], dropna=False).size().rename("rows").reset_index(), use_container_width=True, hide_index=True)
    elif section == "Sensitivity Analysis":
        st.caption("Current sensitivity varies evidence floors. Pressure boundary alternatives and leave-one-season-out fits remain research work; do not read these as a full robustness certification.")
        st.dataframe(r["sensitivity"], use_container_width=True, hide_index=True)
    elif section == "Export Centre":
        files = sorted(OUT.glob("*.csv")) + sorted(OUT.glob("*.json"))
        for path in files:
            if path.suffix == ".csv":
                st.download_button(f"Download {path.name}", path.read_bytes(), path.name, "text/csv", key=path.name)
            else:
                st.download_button(f"Download {path.name}", path.read_bytes(), path.name, "application/json", key=path.name)

