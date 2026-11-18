# TASK-METH-001 — Consolidated Batting and Bowling Methodology v0.2.2

**Package version:** v0.2.2  
**Base version:** v0.2.1  
**Package status:** DRAFT — FOR FORMAL METHODOLOGY APPROVAL  
**Stage 1 formal methodology approval:** PENDING  
**Stage 2 statistical implementation authorization:** NOT GRANTED  
**Independent review response:** Corrections documented; reviewer confirmation pending  
**Conceptual design status:** CLOSED BY PROJECT-OWNER DIRECTION, 16 November 2026; clarifications and review responses incorporated 17 November 2026

## 1. Purpose and decision boundary

This version consolidates the owner-directed conceptual batting and bowling methodology and records the adoption of D-SHR-07 through D-SHR-14. Conceptual design is closed for this phase; the consolidated method still requires an owner decision record, independent statistical review, a formal methodology approval record, and version-controlled approval evidence. Closure of conceptual design does not mean formal approval.

No statistical implementation, production-data access, source reconciliation, metric calculation, player comparison, ranking, or recommendation is authorized. No player-level analysis or ranking is provided. Implementation requires a separate explicit authorization after Stage 1 is complete.

## 2. Consolidated architecture and cross-layer controls

The conceptual architecture remains:

1. **Situational pressure and team task.** Identify the team task from information available before the evaluated event. Batting and bowling pressure states are distinct.
2. **Player responsibility, role and opportunity.** Establish the individual’s actual eligible exposure and responsibility. Partnership and opposing-batter information are context, not automatic individual credit.
3. **Historical expectation and baseline.** Use prior-only player-specific history and validated comparable-player adjustment. No future or post-event information may enter the baseline.
4. **Observed performance and pressure response.** Evaluate separate outcome dimensions relative to the defined expectation. Effectiveness is relative performance; consistency is repeatability.
5. **Evidence reliability and uncertainty.** Assess source, attribution, coverage, sample sufficiency and uncertainty. Reliability is separate from performance and consistency.

Provenance and integrity, operational definitions, attribution and denominator validity, data quality and coverage, leakage prevention, statistical validity/uncertainty, and independent verification are cross-layer controls. Readiness is metric-by-metric. A blocked metric does not automatically block an independently validated metric. A ready metric does not itself authorize composite scores, player selection, or rankings.

## 3. Batting methodology

### 3.1 Separate innings populations and pre-event pressure

Maintain separate first-innings and second-innings analytical populations. Define first-innings setting-total pressure as a distinct team task and second-innings chase pressure separately. Do not transfer chase variables to first-innings batting.

Operational pressure classification may be performed only after the relevant innings-specific team-task definition, required source fields and timestamps, operational rules and metric-specific readiness gates have been validated and approved.

Until those conditions are met, an opportunity must remain **UNCLASSIFIED** or **NOT CLASSIFIABLE**. Unclassified must not be interpreted as a non-pressure opportunity.

This conceptual methodology does not assign operational pressure labels to batting opportunities. First-innings operational classification and any other classification requiring unresolved definitions or source fields remain deferred. No operational pressure labels are produced in this documentation package.

Second-innings chase context may include required scoring task/pace, balls remaining, wickets/resources remaining and pre-event match state. Innings stage alone is not pressure. No numerical thresholds or weights are established. Operational rules require validated inputs, rationale, sensitivity analysis and formal approval before player outcomes are examined.

### 3.2 Responsibility, exposure and partnership context

Use actual individual eligible exposure and pre-event responsibility. Batter identity, faced-ball status, event attribution and the eligible denominator must be validated. Partnership state, partner/opposing-batter characteristics and remaining resources may contextualize the team task, but shared partnership outcomes are not automatically credited to an individual batter. Stabilization and acceleration are situational responsibilities only when identified from pre-event role/task information; do not label them retrospectively from the eventual score.

### 3.3 Outcomes and baselines

Keep batting scoring contribution and dismissal outcomes separate. Candidate measures include scoring rate, boundary rate and batter-attributed dismissal rate, each with its own definition, eligible exposure and uncertainty. Dismissals must use an approved batter-attribution and not-out/incomplete-innings rule. Do not combine these outcomes using an unapproved weighting.

Use a prior-only, player-specific historical baseline. Apply comparable-player or role adjustment only when the comparison population and adjustment have been validated. Restrict baseline information to records available before the evaluated event. Keep role/phase, competition and season comparability explicit; do not silently pool IPL and T20I evidence.

### 3.4 Effectiveness, consistency and reliability

Pressure effectiveness is the evaluated batting outcome relative to the historical expectation/baseline for comparable opportunities. Pressure consistency remains a conceptual repeatability dimension, not an approved estimable metric. Before any consistency metric is READY, define its estimand and comparable-opportunity population, separate real performance variation from sampling noise, specify match/player dependence and uncertainty treatment, and document validation. Raw dispersion or low variance alone is not pressure consistency. Evidence reliability separately reports source validity, opportunity coverage, sample sufficiency and uncertainty. These are not a single score.

## 4. Bowling methodology

### 4.1 Separate innings populations and pre-event pressure

Maintain separate first-innings and second-innings analytical populations. Define the first-innings restricting task separately from the second-innings defending task. In a chase-defense state, candidate context includes target/current score, opponent required pace or score gap, balls and wickets remaining, and the state at the time before the evaluated delivery. An over being late is not sufficient to establish pressure. No numerical thresholds or universal weighting are established.

### 4.2 Responsibility, actual exposure and context

Use actual eligible deliveries and the bowler’s assigned role/phase. Distinguish intended/assigned overs from deliveries actually bowled. Partnership and opposing-batter information can describe the task but do not automatically establish individual bowler credit. Attribute outcomes to the bowler only under validated event rules.

### 4.3 Separate outcomes and data requirements

Keep run containment and bowler-credit wicket contribution separate. Candidate dimensions include economy/containment, bowler-credit wicket rate and dot-ball rate, but they require distinct validated definitions and denominators. Do not use dismissals as a substitute for bowler-credit wickets, and do not impose a universal fixed weighting between containment and wickets.

Delivery identity, legal-ball classification, extras, non-legal deliveries, team/batter/bowler run allocation, wicket type and bowler credit must be validated. Full-population bowler-conceded runs are **NOT FEASIBLE under current evidence**; a restricted population requires separate evidence and approval and cannot be silently substituted.

### 4.4 Baselines and response dimensions

Use prior-only bowler-specific history with validated comparable-player/role adjustment. Keep spell-wide description distinct from pressure-specific response. Pressure effectiveness is pressure outcome relative to historical expectation for comparable role/exposure. Pressure consistency remains a conceptual repeatability dimension, not an approved estimable metric. Before any consistency metric is READY, define its estimand and comparable-opportunity population, separate real variation from sampling noise, specify match/player dependence and uncertainty treatment, and document validation. Raw dispersion or low variance alone is not pressure consistency. Reliability, sample sufficiency and uncertainty are reported separately. Recovery after an expensive over remains deferred as a separate sequential question because post-hoc selection, role assignment and regression-to-the-mean require a distinct design.

## 5. Adopted shared safeguards

The project owner adopted the following conceptual safeguards on **16 November 2026**. Adoption is not formal methodology approval or implementation authorization.

| Decision | Adopted safeguard |
|---|---|
| D-SHR-07 | **Dependence:** assess multiple deliveries within matches, repeated observations of players across matches, shared match conditions between players, and spell dependence where supported by the data and estimand. Do not treat these observations as independent. No estimator is selected; validate the dependence and uncertainty method before affected metrics pass the statistical-validity gate or support player comparisons. |
| D-SHR-08 | **Small samples:** use partial pooling or shrinkage only when validated. Show raw evidence and uncertainty. No method or numeric minimum is selected by this record. |
| D-SHR-09 | **Selection and opportunity bias:** account for role, selection and actual exposure; report opportunity limitations. |
| D-SHR-10 | **Information leakage:** use only information available before the evaluated event. Keep match result/future information out of pressure classification and predictors. |
| D-SHR-11 | **Metric overlap:** prevent double-counting and preserve separate performance dimensions; no composite is approved. |
| D-SHR-12 | **Minimum evidence:** establish requirements through historical validation. Report inconclusive results instead of forcing rankings. No numeric threshold is selected. |

These safeguards do not close PA-OQ items about estimator choice, cutoffs, sample rules or validation details; those source questions remain OPEN.

## 6. Adopted D-SHR-13 — metric-by-metric readiness

The project owner adopted D-SHR-13 on **16 November 2026**. Every metric is assessed independently against all seven gates:

1. Source provenance and integrity.
2. Operational definition.
3. Attribution and denominator validation.
4. Data quality and coverage.
5. Leakage prevention.
6. Statistical validity and uncertainty treatment.
7. Independent verification.

For each metric, maintain a metric-level readiness evidence record documenting: (1) metric identifier and operational definition; (2) source paths/identities and provenance; (3) attribution rules and denominator validation; (4) data quality and population coverage; (5) leakage prevention tests and event-time cutoffs; (6) statistical estimator and uncertainty treatment, where applicable; (7) validation evidence and test results; (8) independent reviewer identity and verification outcome; (9) explicit limitations and permitted analytical use; (10) analyst/preparer and project-owner readiness decision and sign-off; and (11) explicit **NO-RANK** or **INCONCLUSIVE** outcome when evidence is insufficient. No metric status is upgraded in v0.2.2.
Allowed readiness outcomes are **READY**, **READY WITH LIMITATIONS**, and **NOT READY**. A metric-specific gate failure keeps that metric from a higher status; one blocked metric does not automatically prevent an independently validated metric from being assessed. A metric readiness outcome is not authorization for composite scores, player selection, ranking, or production execution. No metric status is upgraded by this conceptual adoption record.

## 7. Adopted D-SHR-14 — separate approval stages

The project owner adopted D-SHR-14 on **16 November 2026**.

### Stage 1 — Methodology approval

Requires the consolidated batting and bowling methodology, an owner decision record, independent statistical review, a formal methodology approval record, and version-controlled approval evidence. Stage 1 remains **PENDING**. Conceptual design closure and adoption of safeguards do not satisfy formal approval.

### Stage 2 — Implementation authorization

Requires separate explicit authorization identifying:

- The approved methodology and implementation specification.
- Exact source inputs and hashes.
- Exact implementation code and hash.
- Approved execution directory.
- Permitted operations and outputs.
- Required tests and independent verification.
- Stop conditions and evidence-preservation requirements.

Stage 2 is **NOT GRANTED**. Methodology approval must never automatically authorize production-data access or statistical execution. The accompanying `IMPLEMENTATION_AUTHORIZATION_GATE_v0_2_2.md` preserves this separation.

## 8. Readiness limitations and unresolved questions

The pressure methodology remains DRAFT — NOT APPROVED pending Stage 1. All `PA-OQ-001` through `PA-OQ-016` remain **OPEN** in the source register. Owner adoption of safeguards narrows the design direction but does not close open questions whose operational details, evidence or approval remain unresolved.

Known dependencies remain: batter-faced and legal-ball classification; batter-run attribution; dismissal taxonomy and innings completion; boundary event definition; bowling legal-ball/extras/non-legal delivery classification; bowler-conceded run allocation; wicket taxonomy and bowler credit; role and actual exposure; time-safe historical baselines; competition/season comparability; and validated historical data for sample, shrinkage, uncertainty and validation rules. Full-population bowler-conceded runs remain not feasible under current evidence.

Historical findings remain unchanged. TASK-001.2 structural profiling recorded `playing_eleven` candidate key `(match_id, team_id, player_id)` failure: 35 duplicate groups, 40 excess duplicate rows, 75 rows in duplicate groups, maximum multiplicity 3, and null key count 0; root cause was not established and no repair is inferred. DQF-001 remains OPEN. The 30-versus-26 source-parent discrepancy remains unresolved. M2.6 remains NOT READY. TASK-001.4 OQ-001–OQ-013 remain OPEN, and the source comparison remains PARTIAL — BLOCKED. The independent review found a 13-field header and a 14-field intermediate `NOT_RUN` row in `changed_value_summary.csv`; six payload hashes matching its manifest do not establish semantic or structural validity. Reconciliation conclusions and metric-readiness impacts remain NOT VERIFIED. The blocked run and its seven outputs were not accessed or modified for this package.

The status `OWNER-ADOPTED CONCEPT — FORMAL APPROVAL PENDING` in the decision register means only that conceptual direction is adopted. No finding in the independent statistical review is declared closed; reviewer confirmation remains required. It does not upgrade metric readiness, remove data blockers, resolve every related PA-OQ, or authorize implementation.

## 9. Approval and execution status

This package is for formal methodology approval and independent statistical review. The owner-adopted conceptual framework is **not** formal methodology approval, statistical implementation approval, production-data access authorization, or execution authorization. No implementation or analysis is authorized by this package. Stop after owner and independent review; any later implementation requires a distinct Stage 2 authorization.

## v0.2.1 owner clarification — 17 November 2026

The owner adopted D-SHR-03 through D-SHR-05 as concepts, each with status **OWNER-ADOPTED CONCEPT — FORMAL APPROVAL PENDING**:

- **D-SHR-03 — Prior-only historical baseline:** Use only information available before the evaluated event. Player-specific history is primary; comparable-player adjustments are permitted only when validated. Exact lookback periods, timestamp cutoffs, historical coverage rules and adjustment parameters remain open pending validation.
- **D-SHR-04 — IPL and T20I comparability:** Keep estimates separate by default. Pooling requires comparability evidence, sensitivity testing and explicit owner approval. IPL evidence is primary for the IPL auction objective. T20I evidence may be supplementary context and must not be silently pooled into IPL rankings.
- **D-SHR-05 — Overall and role-adjusted comparisons:** Report overall and supported role/phase-specific performance separately. Adjustments must be predeclared, justified and validated. Do not force a single cross-role ranking when comparability is unsupported.

All existing PA-OQ mappings remain, and PA-OQ-001 through PA-OQ-016 remain OPEN.

D-BAT-01 records separate first-innings and second-innings batting populations. First-innings setting-total pressure is a distinct conceptual team task; second-innings chase pressure is separate. Chase variables are not transferred to first-innings batting. Operational thresholds, pressure classification and statistical calculation are deferred until defensible historical expectations and source fields are validated.

The five-layer framework, separate outcome dimensions, personal baselines, effectiveness, consistency, uncertainty and evidence reliability remain intact. D-SHR-07 through D-SHR-14 retain their adopted framework and safeguards. Formal methodology approval remains PENDING; statistical implementation authorization remains NOT GRANTED.
## 10. v0.2.2 response to independent review

This additive version uses v0.2.1 as its predecessor. It resolves the conditional-classification wording conflict and identifies the package version and base version explicitly. The v0.2.1 authorization gate is preserved unchanged; this package supplies a version-specific successor gate. Batting and bowling scenarios now include interrupted/revised-target cases, conditional on verified event-time data. D-SHR-07 explicitly requires assessment of match, player, shared-match and supported spell dependence without selecting an estimator. D-SHR-06, D-BAT-10 and D-BWL-11 keep consistency conceptual until a validated estimable specification exists. D-SHR-13 requires a metric-level readiness evidence record with the listed evidence and sign-offs. No metric status is upgraded. METH-REV-001 through METH-REV-007 are addressed in documentation but none is declared closed pending independent reviewer confirmation.