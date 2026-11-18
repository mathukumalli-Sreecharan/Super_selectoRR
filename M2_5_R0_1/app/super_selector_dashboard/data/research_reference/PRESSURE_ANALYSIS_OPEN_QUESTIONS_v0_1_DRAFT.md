# Pressure Analysis Open Questions v0.1

**Status: DRAFT - NOT APPROVED. Every item below is OPEN.** These are planning questions only; no decision is made by this register. They do not close, replace, or change TASK-001.4 OQ-001 through OQ-013.

| ID | Open question | Why a decision is needed | Required decision owner/evidence |
|---|---|---|---|
| PA-OQ-001 | Which pressure-state variables define batting pressure? | Required rate, wickets, balls, innings stage, and match state can classify different populations. | Project owner and technical reviewer; documented rationale and sensitivity plan. |
| PA-OQ-002 | Which variables define bowling pressure, and how should defending and chasing contexts differ? | Bowling tasks differ by match state and role; batting definitions cannot be copied mechanically. | Project owner and technical reviewer. |
| PA-OQ-003 | What numerical cutoffs, if any, should be used for candidate pressure indicators? | No thresholds are set here; they must not be invented or tuned to desired rankings. | Evidence review, prespecified rationale, sensitivity and out-of-sample validation, then approval. |
| PA-OQ-004 | Which innings-stage and role/phase groupings are supportable? | Phase and role may confound player comparisons and data may not support every split. | Field coverage review and approval. |
| PA-OQ-005 | Which batting and bowling metrics are sufficiently defined and data-ready? | Legal-ball, batter-faced, wicket-credit, and bowler-conceded limitations constrain candidates. | Metric-specific data-quality evidence and independent review. |
| PA-OQ-006 | What is the approved metric-specific minimum sample requirement? | Different metrics and player roles have different exposure and uncertainty. | Evidence-backed rule for each metric; no numeric value is proposed here. |
| PA-OQ-007 | How should low, medium, high, and insufficient evidence be operationalized? | Qualitative labels need reproducible criteria and must not be mistaken for player grades. | Approved coverage, sample, uncertainty, and stability criteria. |
| PA-OQ-008 | Which uncertainty method and any shrinkage/partial-pooling approach are appropriate? | Delivery observations cluster within matches and small samples can be unstable. | Technical review, simulation or validation evidence, and approval. |
| PA-OQ-009 | Which contextual controls are supportable for opposition, venue, competition, season, role, and match state? | Controls can reduce confounding but may be unavailable or overfit sparse populations. | Field mapping, coverage evidence, prespecified model specification. |
| PA-OQ-010 | What temporal or independent validation split should be used? | Pressure definitions and rankings require evaluation outside the data used to shape them. | Approved season/population split and leakage audit. |
| PA-OQ-011 | How should survivorship, participation selection, missingness, and role changes be reported? | Players with observed pressure opportunities may differ systematically from those without them. | Approved inclusion/exclusion rules and sensitivity plan. |
| PA-OQ-012 | Under what evidence conditions may a player enter a top-10 list, and how are ties or insufficient cases handled? | Rankings can hide uncertainty and should not force a list when evidence is inadequate. | Owner-approved eligibility, uncertainty, tie-break, and no-rank rules. |
| PA-OQ-013 | What minimum evidence is required before squad-strengthening or auction implications are discussed? | Descriptive associations alone do not establish player value or causal impact. | Separate owner approval, independent review, and explicit decision criteria. |
| PA-OQ-014 | May match result be used as an outcome label, and what leakage controls are mandatory? | Post-match information must not enter delivery-time pressure classification or predictors. | Approved label design and leakage review. |
| PA-OQ-015 | What source access, implementation, and analysis authorizations are needed after the blocked TASK-001.4 run? | This planning package authorizes no dataset access or analytics; the prior run remains PARTIAL - BLOCKED. | Separate explicit owner authorizations and technical review; do not reuse or repair the blocked run. |
| PA-OQ-016 | How should known readiness limitations and excluded metrics appear in the final presentation? | Legal-ball/batter-faced coverage, bowler-conceded feasibility, participation-only counts, match-result leakage, and bowling-speed exclusion must remain visible. | Owner and technical reviewer sign-off on disclosure language. |

## Status control

All PA-OQ items remain OPEN until the competent project authority records an explicit decision. No pressure thresholds, sample floors, metric readiness upgrades, player rankings, or recommendations are approved by this document.