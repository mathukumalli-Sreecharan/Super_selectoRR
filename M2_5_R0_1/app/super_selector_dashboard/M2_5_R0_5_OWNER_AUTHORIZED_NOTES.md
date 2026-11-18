# M2_5_R0_6 — Direct IPL data execution

- Real IPL mode now opens the bundled owner-supplied archive directly.
- Removed the authorization-gate call from the production CSV loader and the active dashboard path.
- No trust-anchor registry, authorization record, external certificate, or authority portal is required for local data access.
- Archive/member hashes remain as file-integrity checks only.
- Real IPL 2022–2026 filtering is based on competition IDs in the supplied competitions/matches files.
- Automatically selects Top 10 batters (runs, strike-rate tiebreak) and Top 10 bowlers (bowler-credited wickets, economy tiebreak).
- These leaderboards are descriptive IPL statistics, not pressure-scenario rankings.
- Real source loading and leaderboard calculation were executed in this environment; full Streamlit UI and full pytest suite have not been run here.
