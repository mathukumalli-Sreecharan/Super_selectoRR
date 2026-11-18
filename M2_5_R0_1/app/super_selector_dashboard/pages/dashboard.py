from __future__ import annotations

import pandas as pd
import streamlit as st

from services.pressure_product import METHODOLOGY, OUT, build_product

PAGES = (
    "Executive Overview", "Top 10 Pressure Batters", "Top 10 Pressure Bowlers",
    "Batting Pressure Analytics", "Bowling Pressure Analytics", "Scenario Explorer",
    "Player Deep Dive", "Match and Delivery Explorer", "Pressure vs Normal Comparison",
    "Consistency and Reliability", "Ranking Methodology", "Export Centre",
)


@st.cache_data(show_spinner="Preparing the IPL delivery analysis…")
def _analytics():
    return build_product(write=True)


def _style():
    st.markdown("""
    <style>
      :root { --navy:#10283F; --navy2:#1C3A52; --green:#557A61; --green-pale:#EEF3EE; --ink:#172633; --muted:#657582; --line:#D8E0E5; --paper:#F7F9FA; }
      .stApp { background:#F7F9FA; color:var(--ink); }
      [data-testid="stHeader"] { background:rgba(247,249,250,.92); }
      [data-testid="stSidebar"] { background:#10283F; border-right:1px solid #294256; }
      [data-testid="stSidebar"] * { color:#E8EEF2 !important; }
      [data-testid="stSidebar"] [data-testid="stRadio"] label { padding:5px 0; }
      h1,h2,h3 { color:#10283F; letter-spacing:-.025em; }
      h1 { font-weight:680; font-size:2.05rem; }
      h2 { font-weight:650; font-size:1.35rem; margin-top:1.2rem; }
      h3 { font-weight:620; font-size:1.08rem; }
      p,li { line-height:1.55; }
      .report-kicker { color:#557A61; font-size:.73rem; font-weight:700; letter-spacing:.13em; text-transform:uppercase; margin:0 0 .45rem 0; }
      .report-deck { color:#536675; font-size:1rem; max-width:900px; margin:.1rem 0 1rem; }
      .status-line { border-left:3px solid #557A61; background:#EEF3EE; padding:.75rem 1rem; color:#34483B; margin:.8rem 0 1.25rem; }
      .section-rule { border:0; border-top:1px solid #D8E0E5; margin:1.4rem 0; }
      [data-testid="stMetric"] { background:#FFFFFF; border:1px solid #D8E0E5; border-radius:3px; padding:12px 14px; }
      [data-testid="stMetricLabel"] { color:#657582; font-size:.78rem; }
      [data-testid="stMetricValue"] { color:#10283F; font-weight:680; }
      [data-testid="stDataFrame"] { border:1px solid #D8E0E5; }
      [data-testid="stAlert"] { border-radius:2px; }
      div.stButton > button, div.stDownloadButton > button { border-radius:2px; border:1px solid #557A61; color:#244D36; }
      div.stButton > button:hover, div.stDownloadButton > button:hover { border-color:#10283F; color:#10283F; }
    </style>
    """, unsafe_allow_html=True)


def _intro(kicker: str, title: str, deck: str):
    st.markdown(f'<div class="report-kicker">{kicker}</div><h1>{title}</h1><div class="report-deck">{deck}</div>', unsafe_allow_html=True)


def _table(frame: pd.DataFrame, *, hide_index=True, height=None):
    options = {"width": "stretch", "hide_index": hide_index}
    if height is not None:
        options["height"] = height
    st.dataframe(frame, **options)


def _format_ranking(table: pd.DataFrame, discipline: str) -> pd.DataFrame:
    bat = discipline == "batting"
    cols = ["rank", "striker_name" if bat else "bowler_name", "teams",
            "pressure_strike_rate" if bat else "pressure_economy",
            "delta_vs_prior", "scenario_contribution", "opportunities" if bat else "legal_balls",
            "matches", "seasons", "reliability", "eligibility_status"]
    view = table[[c for c in cols if c in table]].copy()
    return view.rename(columns={
        "rank": "Rank", "striker_name": "Batter" if bat else "Player", "bowler_name": "Bowler",
        "teams": "IPL teams represented", "pressure_strike_rate": "Pressure strike rate",
        "pressure_economy": "Pressure economy", "delta_vs_prior": "Pressure-to-baseline difference",
        "scenario_contribution": "Scenario contribution", "scenario_coverage": "Scenario count", "opportunities": "Balls faced", "legal_balls": "Legal balls bowled",
        "matches": "Matches", "seasons": "Seasons", "reliability": "Evidence coverage",
        "eligibility_status": "Evidence status",
    })


def _evidence_panel(r, discipline: str, player_name: str):
    bat = discipline == "batting"
    d = r["deliveries"]
    namecol = "striker_name" if bat else "bowler_name"
    flag = "batting_pressure" if bat else "bowling_pressure"
    player_rows = d[(d[namecol] == player_name) & d[flag].fillna(False)].copy()
    if player_rows.empty:
        st.info("No classified pressure deliveries are available for this player in the current source coverage.")
        return
    cols = ["delivery_ref", "season", "match_id", "innings", "innings_ball_num", "score_before", "wickets_before",
            "legal_balls_remaining", "required_run_rate", "phase", "delivery_batter_runs", "delivery_bowler_runs",
            "delivery_outcome_wicket", "state_status"]
    st.markdown("**Selected delivery evidence**")
    st.caption("Source reference: match ID : innings : innings_ball_num. Pre-delivery state and outcome are shown separately.")
    _table(player_rows[cols].head(40))


def _ranking_page(r, discipline: str):
    bat = discipline == "batting"
    label = "batters" if bat else "bowlers"
    rank_table = r["bat_rankings"] if bat else r["bowl_rankings"]
    title = "Top 10 pressure batters" if bat else "Top 10 pressure bowlers"
    measure = "pressure strike rate" if bat else "pressure economy"
    _intro("IPL 2022–2026 · Provisional research ordering", title,
           f"Ordered by {measure} relative to each player's prior-only baseline. Scenario exposure and represented matches provide context; no composite score is used.")
    st.markdown('<div class="status-line">The pressure definition and evidence floor are provisional research choices. Treat these lists as descriptive findings, not approved player-quality rankings.</div>', unsafe_allow_html=True)
    if rank_table.empty:
        st.info("No player met the current evidence floor. No positions are filled without evidence.")
        return
    floors = sorted(rank_table.matches.dropna().astype(int).unique())
    floor = st.select_slider("Minimum represented matches", options=floors, value=min(5, max(floors))) if floors else 1
    visible = rank_table[rank_table.matches >= floor].copy()
    visible = visible.head(10).copy()
    visible.insert(0, "rank_display", range(1, len(visible) + 1))
    visible = visible.drop(columns=["rank"]).rename(columns={"rank_display": "rank"})
    _table(_format_ranking(visible, discipline))
    st.caption(f"{len(rank_table):,} players meet the current five-match/30-opportunity research floor before this filter. Data version {r['data_version']}; methodology {r['methodology_version']}.")
    if len(rank_table) > 10:
        st.markdown("**Next eligible candidates**")
        next_rows = rank_table[rank_table.matches >= floor].iloc[10:15].copy()
        if not next_rows.empty:
            next_rows.insert(0, "rank_display", range(11, 11 + len(next_rows)))
            next_rows = next_rows.drop(columns=["rank"]).rename(columns={"rank_display": "rank"})
            _table(_format_ranking(next_rows, discipline))
    names = rank_table["striker_name" if bat else "bowler_name"].tolist()
    chosen = st.selectbox("Open delivery evidence", names[:10], key=f"evidence_{discipline}")
    _evidence_panel(r, discipline, chosen)


def _scenario_explorer(r):
    _intro("Situation analysis", "Scenario explorer", "Inspect delivery-level exposure and pre-delivery context for each batting and bowling scenario.")
    discipline = st.radio("Discipline", ["Batting", "Bowling"], horizontal=True)
    scenarios = [f"B{i}" for i in range(1, 11)] if discipline == "Batting" else [f"W{i}" for i in range(1, 7)]
    scenario = st.selectbox("Scenario definition", scenarios)
    st.caption(METHODOLOGY["scenarios"].get(scenario, "Definition unavailable"))
    d = r["deliveries"]
    result = d[d[scenario].fillna(False)].copy()
    seasons = sorted(result.season.dropna().astype(int).unique().tolist())
    selected_seasons = st.multiselect("Seasons", seasons, default=seasons)
    namecol = "striker_name" if discipline == "Batting" else "bowler_name"
    selected_player = st.selectbox("Player", ["All players"] + sorted(result[namecol].dropna().unique().tolist()))
    result = result[result.season.isin(selected_seasons)]
    if selected_player != "All players": result = result[result[namecol] == selected_player]
    st.metric("Classified delivery exposures", f"{len(result):,}")
    cols = ["delivery_ref", "season", "match_id", "innings", "striker_name", "bowler_name", "score_before", "wickets_before", "legal_balls_remaining", "required_run_rate", "phase", "delivery_batter_runs", "delivery_bowler_runs", "delivery_outcome_wicket", "state_status"]
    _table(result[cols].head(1000))


def _player_deep_dive(r):
    _intro("Performance dossier", "Player evidence profile", "A player-level summary of pressure outcomes, scenario exposure, season repeatability and source-linked deliveries.")
    discipline = st.radio("Discipline", ["Batter", "Bowler"], horizontal=True)
    bat = discipline == "Batter"
    table = r["bat_rankings"] if bat else r["bowl_rankings"]
    namecol, idcol = ("striker_name", "striker_id") if bat else ("bowler_name", "bowler_id")
    if table.empty:
        st.info("No eligible players in the current research run.")
        return
    choices = table[[namecol, idcol]].drop_duplicates()
    choice_map = {f"{row[namecol]} · ID {row[idcol]}": (row[namecol], row[idcol]) for _, row in choices.iterrows()}
    selected_label = st.selectbox("Player", list(choice_map))
    name, pid = choice_map[selected_label]
    row = table[table[idcol].astype(str).eq(str(pid))].iloc[0]
    a, b, c, d = st.columns(4)
    a.metric("Rank", f"#{int(row['rank'])}")
    a_name = "pressure_strike_rate" if bat else "pressure_economy"
    a.metric("Pressure strike rate" if bat else "Pressure economy", f"{row[a_name]:.1f}")
    b.metric("Pressure-to-baseline difference", f"{row['delta_vs_prior']:+.1f}")
    c.metric("Represented matches", f"{int(row['matches'])}")
    d.metric("Scenario coverage", f"{int(row['scenario_coverage'])}")
    st.markdown(f"**Teams represented:** {row.get('teams', 'Not available')}  \n**Evidence coverage:** {row['reliability']} · {int(row['opportunities'])} {'balls faced' if bat else 'legal balls'}")
    st.subheader("Pressure performance and baseline")
    if bat:
        st.write(f"Pressure strike rate was **{row['pressure_strike_rate']:.1f}**. The prior-only baseline was **{row['baseline_strike_rate']:.1f}**, a difference of **{row['delta_vs_prior']:+.1f} runs per 100 balls**.")
    else:
        st.write(f"Pressure economy was **{row['pressure_economy']:.2f}**. The prior-only baseline was **{row['baseline_economy']:.2f}**, a reduction of **{row['delta_vs_prior']:.2f} runs per six legal balls**.")
    st.caption("The prior-only baseline uses earlier IPL delivery observations. It is separate from a matched non-pressure comparison and is not adjusted for phase or role.")
    scenario_table = r["batting_scenarios"] if bat else r["bowling_scenarios"]
    scenario_rows = scenario_table[scenario_table.player_id.astype(str).eq(str(pid))].copy()
    st.subheader("Scenario-by-scenario performance")
    if not scenario_rows.empty:
        scenario_metric = "pressure_strike_rate" if bat else "pressure_economy"
        scenario_rows = scenario_rows.sort_values("scenario")
        chart = scenario_rows.set_index("scenario")[[scenario_metric]]
        st.bar_chart(chart, y=scenario_metric, x_label="Scenario", y_label="Strike rate" if bat else "Runs per six legal balls", height=280)
        _table(scenario_rows[["scenario", "opportunities", "matches", scenario_metric, "delta_vs_prior", "reliability", "eligibility_status"]])
    events = r["deliveries"]
    event_id = "striker_id" if bat else "bowler_id"
    pressure_key = "batting_pressure" if bat else "bowling_pressure"
    season_events = events[(events[event_id].astype(str) == str(pid)) & events[pressure_key].fillna(False)].copy()
    outcome = "delivery_batter_runs" if bat else "delivery_bowler_runs"
    event_exposure = "batter_faced" if bat else "legal_ball"
    season_metrics = season_events.groupby("season").agg(opportunities=(event_exposure, "sum"), pressure_deliveries=("delivery_ref", "count"), matches=("match_id", "nunique"), outcome=(outcome, "sum")).reset_index()
    denominator = season_metrics.opportunities.replace(0, pd.NA)
    season_metrics["outcome_rate"] = season_metrics.outcome / denominator * (100 if bat else 6)
    st.subheader("Season-level repeatability")
    if not season_metrics.empty:
        st.bar_chart(season_metrics.set_index("season")[["outcome_rate"]], y="outcome_rate", x_label="IPL season", y_label="Strike rate" if bat else "Economy", height=240)
        _table(season_metrics)
    _evidence_panel(r, "batting" if bat else "bowling", name)
    st.subheader("Ranking interpretation and limitations")
    position = int(row["rank"])
    next_row = table[table["rank"] == position + 1]
    next_note = ""
    if not next_row.empty:
        next_player = next_row.iloc[0]
        next_note = f" The next candidate is {next_player[namecol]}, with a pressure-to-baseline difference of {next_player['delta_vs_prior']:+.1f}."
    st.write(f"The player ranks on a pressure-to-baseline difference of {row['delta_vs_prior']:+.1f}, with {row.get('scenario_contribution', 'no scenario list')} represented and {int(row['matches'])} matches. Observed match-level standard deviation: {row.get('match_level_consistency_sd', float('nan')):.1f}; this describes dispersion and is not an uncertainty interval.{next_note}")
    st.caption("Pressure boundary, scenario definitions and minimum evidence floor are provisional. The estimates are descriptive and not role-adjusted.")


def _pressure_normal(r):
    _intro("Comparative analysis", "Pressure and non-pressure performance", "Compare measured outcomes in classified pressure and non-pressure deliveries. Prior-only baselines are reported separately.")
    d = r["deliveries"].copy()
    discipline = st.radio("Discipline", ["Batting", "Bowling"], horizontal=True)
    bat = discipline == "Batting"
    flag = "batting_pressure" if bat else "bowling_pressure"
    player_id = "striker_id" if bat else "bowler_id"
    player_name = "striker_name" if bat else "bowler_name"
    outcome = "delivery_batter_runs" if bat else "delivery_bowler_runs"
    exposure = "batter_faced" if bat else "legal_ball"
    rate_scale = 100 if bat else 6
    valid = d[outcome].notna() & pd.to_numeric(d[exposure], errors="coerce").eq(1)
    eligible = d[valid & d.state_status.eq("RECONSTRUCTED")].copy()
    eligible["classification"] = eligible[flag].fillna(False).map({True: "Pressure", False: "Non-pressure"})
    grouped = eligible.groupby([player_id, player_name, "classification"]).agg(outcome_total=(outcome, "sum"), opportunities=(exposure, "sum"), matches=("match_id", "nunique")).reset_index()
    grouped["rate"] = grouped.outcome_total / grouped.opportunities.replace(0, pd.NA) * rate_scale
    players = sorted(grouped[player_name].dropna().unique().tolist())
    chosen = st.selectbox("Player", players)
    player = grouped[grouped[player_name] == chosen]
    _table(player)
    if not player.empty:
        st.bar_chart(player.set_index("classification")[["rate"]], y="rate", x_label="Delivery classification", y_label="Strike rate" if bat else "Economy", height=260)
        st.caption(f"Observed result across {int(player.matches.max())} matches. Non-pressure comparison uses valid non-pressure deliveries in the reconstructed-state population.")


def render_dashboard(section: str) -> None:
    _style()
    r = _analytics()
    qa = r["quality"].set_index("item")["value"].to_dict()
    if section == "Executive Overview":
        _intro("SupeRR Selector · Season 2", "IPL performance under pressure", "Delivery-level analysis across the five supplied IPL seasons, with source traceability and explicit coverage limits.")
        st.markdown('<div class="status-line">Research status: provisional pressure definitions and candidate eligibility floors. Unresolved source rows are excluded from affected state updates; rankings are descriptive.</div>', unsafe_allow_html=True)
        a, b, c, d = st.columns(4)
        a.metric("Matches", f"{r['matches'].match_id.nunique():,}")
        b.metric("Deliveries", f"{len(r['deliveries']):,}")
        c.metric("Player IDs", f"{int(qa['unique_player_ids']):,}")
        d.metric("Classified pressure deliveries", f"{int(qa['pressure_deliveries']):,}")
        st.caption(f"Population: IPL 2022–2026 · Data version {r['data_version']} · Methodology {r['methodology_version']} · Run {r['generated_at_utc']}")
        st.subheader("Leading candidates")
        left, right = st.columns(2)
        with left:
            st.markdown("**Batting**")
            _table(_format_ranking(r["bat_rankings"].head(5), "batting"))
        with right:
            st.markdown("**Bowling**")
            _table(_format_ranking(r["bowl_rankings"].head(5), "bowling"))
        st.markdown("Conventional runs and wickets leaderboards are kept separate from the pressure analysis.")
    elif section == "Top 10 Pressure Batters": _ranking_page(r, "batting")
    elif section == "Top 10 Pressure Bowlers": _ranking_page(r, "bowling")
    elif section == "Batting Pressure Analytics":
        _intro("Batting research", "Batting under pressure", "Scoring rate, dismissal frequency, boundary share and delivery opportunity by player.")
        _table(r["bat_rankings"].sort_values("delta_vs_prior", ascending=False))
    elif section == "Bowling Pressure Analytics":
        _intro("Bowling research", "Bowling under pressure", "Conceded runs, legal-ball economy, wickets and dot-ball pressure by bowler.")
        _table(r["bowl_rankings"].sort_values("delta_vs_prior", ascending=False))
    elif section == "Scenario Explorer": _scenario_explorer(r)
    elif section == "Player Deep Dive": _player_deep_dive(r)
    elif section == "Match and Delivery Explorer":
        _intro("Source evidence", "Match and delivery explorer", "Inspect reconstructed pre-delivery state, the recorded outcome and the resulting state for one IPL innings.")
        d = r["deliveries"]
        matches = sorted(d.match_id.astype(str).unique())
        mid = st.selectbox("Match ID", matches)
        inn = st.selectbox("Innings", sorted(d[d.match_id.astype(str) == mid].innings.astype(str).unique()))
        cols = ["delivery_ref", "striker_name", "non_striker_name", "bowler_name", "score_before", "wickets_before", "wickets_remaining", "legal_balls_remaining", "current_run_rate", "target", "runs_required", "required_run_rate", "phase", "partnership_runs", "pressure", "state_status", "target_status", "delivery_batter_runs", "delivery_bowler_runs", "delivery_outcome_wicket", "score_after", "wickets_after"]
        _table(d[(d.match_id.astype(str) == mid) & (d.innings.astype(str) == inn)][cols])
    elif section == "Pressure vs Normal Comparison": _pressure_normal(r)
    elif section == "Consistency and Reliability":
        _intro("Evidence assessment", "Consistency and reliability", "Match and season coverage are separated from outcome dispersion. Dispersion is descriptive, not a confidence interval.")
        _table(r["reliability"].sort_values(["discipline", "matches"], ascending=[True, False]))
        _table(r["consistency"][[c for c in ["player_id", "discipline", "opportunities", "matches", "seasons", "match_level_consistency_sd", "season_level_consistency_sd", "consistency_status"] if c in r["consistency"]]])
    elif section == "Ranking Methodology":
        _intro("Research specification", "Ranking methodology", "Versioned operational definitions and candidate parameters. Implemented choices remain provisional pending formal review.")
        _table(pd.DataFrame([{"Parameter": "Population", "Definition": METHODOLOGY["population"]}, {"Parameter": "Pressure rule", "Definition": str(METHODOLOGY["provisional_pressure_rule"])}, {"Parameter": "Scenario definitions", "Definition": str(METHODOLOGY["scenarios"])}, {"Parameter": "Known limitations", "Definition": " · ".join(METHODOLOGY["known_limits"])}]))
    elif section == "Data Quality and Coverage":
        _intro("Source audit", "Data quality and coverage", "Hash-verified archive, exact competition filtering, delivery reconciliation and match-state coverage.")
        quality = r["quality"].copy()
        quality["value"] = quality.value.map(str)
        _table(quality)
        st.subheader("Extras reconciliation by source category")
        _table(r["deliveries"].groupby(["extras_type", "attribution_status", "attribution_reason"], dropna=False).size().rename("Delivery rows").reset_index())
    elif section == "Sensitivity Analysis":
        _intro("Robustness review", "Ranking sensitivity", "Candidate lists under alternate evidence floors, pressure boundaries and leave-one-season-out analyses.")
        st.caption("Low overlap across variants signals that the current ordering is sensitive to the research choices. This is not a robustness certification.")
        _table(r["sensitivity"])
    elif section == "Export Centre":
        _intro("Reproducible outputs", "Export centre", "Download the CSV and JSON files generated from this analytical run.")
        for path in sorted(OUT.glob("*.csv")) + sorted(OUT.glob("*.json")):
            mime = "text/csv" if path.suffix == ".csv" else "application/json"
            st.download_button(path.name, path.read_bytes(), path.name, mime, key=path.name)
