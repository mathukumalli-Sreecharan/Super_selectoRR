# Current analytical limitations

- Delivery source semantics conflict with the supplied run interpretation. IPL wides and byes/leg-byes carry extras in `extras1_runs` with `runs=0`; 179 of 257 Overstep rows do not reconcile `runs` with `extras1_runs + extras_2_runs`; all 123 `Other` rows remain unresolved. A total of 302 records are excluded from state updates, leaving 235 of 734 innings with partial reconstructed state.
- The pressure rule, scenario boundaries, 5-match/30-opportunity provisional floor, and tie-break ordering are documented but not formally approved. Sensitivity outputs are generated for coverage floors, alternate pressure definitions, and leave-one-season-out runs.
- Rankings are descriptive player-specific delivery contrasts. They are not role-adjusted, causal, or uncertainty-adjusted. No match-clustered confidence intervals or hierarchical estimator has been implemented.
- B2 cannot distinguish anchor/aggressor responsibility from outcomes using validated pre-event evidence. B6 emits separate low-resource bands but does not make matched-pair causal comparisons. Match stakes and closeness are not scored.
- Revised-target matches have chase pressure unavailable because target effective-time evidence is not present. No DLS target is inferred.
- BWL-S08 recovery after an expensive over remains deferred. Post-wicket same-bowler response is not yet included in ranking metrics.
- The archive includes IPL 2026, but the archive snapshot date is not supplied. The analysis treats its season label as source fact.
- Legacy tests in `task_dash_003`, `task_dash_006a`, `task_dash_008`, and `tests/test_opportunity_evidence.py` include obsolete gate expectations or refer to absent governance/fixture files; those are separate from the active direct-source product path.
