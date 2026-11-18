# Pressure Analysis Methodology v0.1

**Status: DRAFT - NOT APPROVED**  
**Purpose:** Planning proposal only. No pressure analysis, player calculation, ranking, or recommendation has been performed.

## 1. Research objective

After source quality and metric readiness are separately established, assess IPL player performance in defined high-pressure match states to inform Rajasthan Royals' 2027 auction-strategy research. The eventual analysis may present a top 10 batter list, a top 10 bowler list, evidence-backed assessments, reliability classifications, and possible squad or auction implications. Those are target deliverables only; this draft contains no player names, results, rankings, or recommendations.

The primary comparison is each player's performance in pressure situations against that same player's suitable non-pressure baseline. Raw aggregate ranking alone is not an adequate measure of pressure performance.

## 2. Evidence boundary and known constraints

### Known project constraints

The following are carried forward as constraints, not newly measured findings:

- Legal-ball and batter-faced classifications have major unresolved coverage limitations.
- Bowler-conceded runs are not feasible as a full-population metric under the existing evidence.
- Match result may be used only as a match-level label, with controls against outcome leakage.
- Participation counts are descriptive only.
- Bowling speed is excluded.
- TASK-001.4 run RR_SOURCE_RECON_20261115_001 is PARTIAL - BLOCKED. Its independent review found a 13-field header and 14-field intermediate NOT_RUN row in changed_value_summary.csv. The run's reconciliation conclusions and metric-readiness impacts remain NOT VERIFIED.
- DQF-001 remains OPEN; M2.6 remains NOT READY; OQ-001 through OQ-013 remain OPEN; the 30-versus-26 discrepancy remains unresolved.

The independent review is at:
D:Super SelectorM2_5_R0_1governanceTASK_001_4source_update_v0_3TASK_001_4_RR_SOURCE_RECON_20261115_001_Independent_Review_v0_1.md

This planning task did not access source datasets or perform analytics. A future analyst must not treat this methodology draft, a source identity check, equal row counts, or the blocked run as evidence that a metric is ready.

### Proposed future evidence gate

Before analysis, an authorized owner and technical reviewer should identify the accepted source versions, resolve applicable data-quality limitations, confirm metric-specific field definitions and coverage, and approve the analysis population and validation plan. Source access and pressure analysis require their own authorization. No such authorization is requested or granted here.

## 3. Candidate pressure framework

Pressure is a context classification to be evaluated, not a label assigned automatically to every late-innings delivery. Batting and bowling pressure should be defined separately because the relevant objective and decision context differ.

### Candidate batting indicators

Evaluate, subject to validated fields:

- Required run rate relative to the scoring rate needed to reach the target.
- Wickets remaining and the batting side's remaining resources.
- Balls remaining and the match state.
- Innings stage, used as context rather than a pressure definition by itself.
- Match closeness, using a predeclared state representation that does not use future outcome information.

A candidate batting-pressure state should reflect a meaningful chase or innings constraint. A late delivery with a comfortable target position is not automatically pressure.

### Candidate bowling indicators

Evaluate the bowling context from the defending side's perspective, including:

- Opponent required run rate and the gap to the required scoring pace.
- Opponent wickets and balls remaining.
- Target, current score, and whether the state is close or materially favors either side.
- Innings stage and role-specific bowling phase, where the data supports it.

A bowler should not be labeled under pressure merely because the over is late. The definition should capture the task and match state faced by the bowler.

### Threshold selection - unresolved

No numerical thresholds are proposed in this draft. The owner and technical reviewer should select and justify thresholds only after relevant fields and coverage are validated. A future decision should:

1. Define the candidate state variables and their timing, units, and source fields.
2. Establish domain rationale and assess how many player-match opportunities each candidate definition would include.
3. Compare reasonable alternatives for stability, interpretability, and sensitivity across seasons and contexts.
4. Freeze the chosen definition before examining player rankings or auction outcomes.
5. Validate the definition on held-out seasons or another preapproved out-of-sample design.
6. Report sensitivity to alternative definitions and the number of observations classified under each.

Thresholds must not be tuned to produce preferred player names or auction conclusions.

## 4. Player-specific baselines and candidate comparisons

For each player and each approved metric, the future analysis should report separately:

- Performance in the defined pressure population.
- Performance outside pressure in a comparable population.
- The difference from the player's own baseline, with the direction and units stated.
- The number of eligible opportunities and exclusions in both populations.
- An uncertainty interval or other approved uncertainty summary.
- Role, phase, competition, season, opposition, venue, and match-state context where supported.

Comparison populations should be made as comparable as practicable. A batter's pressure innings should not be compared indiscriminately with unrelated roles or phases. A bowler's pressure overs should be interpreted in light of phase and assigned role. Context adjustments must be prespecified and supported by available data; they must not conceal poor coverage or create a causal claim.

A player without an adequate pressure or baseline sample should be classified as insufficient evidence, not assigned a zero or promoted by a raw rate. The analysis should distinguish an observed descriptive difference from an adjusted association and from a causal effect.

## 5. Reliability and evidence classification

A future reliability framework should evaluate data validity, eligible opportunity count, uncertainty, coverage, context comparability, and stability across seasons or definitions. Confidence labels should communicate evidence quality, not player quality.

Proposed qualitative interpretation:

- **High evidence confidence:** validated metric and pressure definition, adequate sample under a separately approved minimum, uncertainty narrow enough for the intended decision, and conclusions reasonably stable under approved sensitivity checks.
- **Medium evidence confidence:** core fields and definitions validated, but sample, uncertainty, context coverage, or sensitivity leaves material caveats.
- **Low evidence confidence:** sparse or uneven opportunities, wide uncertainty, partial field coverage, or substantial sensitivity to the pressure definition.
- **Insufficient evidence:** a required field or attribution is not validated, the approved minimum is not met, or selection/coverage prevents a defensible comparison. Do not rank the player on that metric.

No final sample minimum, confidence cut-point, uncertainty interval method, shrinkage amount, or ranking rule is set here. These require evidence, a written rationale, and project-owner approval before analysis. Candidate statistical approaches may include match-clustered uncertainty estimates or partial pooling to reduce small-sample volatility, but their suitability must be evaluated and approved rather than assumed.

Missing records, substitution and participation selection, role changes, survivor effects, and selective availability of historical fields must be reported. Missingness must not be silently treated as zero performance.

## 6. Candidate metric use and readiness

Candidate metric concepts and prerequisites are listed in PRESSURE_METRIC_DEFINITIONS_v0_1_DRAFT.csv. Each metric remains a proposal. In particular:

- Batter balls faced and legal-ball-dependent metrics must not be used until their classifications and coverage are validated.
- Full-population bowler-conceded runs must not be presented as ready under the existing feasibility limitation.
- Wickets must distinguish dismissal events from bowler-credit wickets.
- Match result is an outcome label only; exclude post-outcome information from predictors, pressure classification, and player-performance features.
- Participation counts may describe exposure but cannot stand in for performance.
- Bowling speed is excluded.

No metric calculations or readiness reclassification were performed for this draft.

## 7. Bias, confounding, and validation plan

A future approved study should:

- Separate batter and bowler roles and use role-appropriate denominators and comparisons.
- Address innings phase and assigned role without treating phase as pressure by itself.
- Consider opposition and venue effects only where identifiers, coverage, and sample support them.
- Separate competition and season effects; report changes in rules, schedules, or data definitions where established.
- Represent match state using information available at the time of the delivery; prevent future-score, final-result, or post-match fields from leaking into classification or features.
- Explain match-state confounding: pressure opportunities are not randomly assigned and often co-occur with role, skill, opposition, and match importance.
- Assess survivorship and selection bias, including which players appear in pressure states and who has enough observations to qualify.
- Prespecify a temporal or otherwise independent validation design and sensitivity checks before reviewing player lists.
- Require validated metric inputs, traceable row populations, uncertainty reporting, and independent technical review before auction implications are considered.

These controls reduce interpretive risk but do not by themselves establish causal effects.

## 8. Final presentation plan

If later authorized and evidence supports it, organize the final presentation as:

1. Executive summary.
2. Research question and methodology.
3. Pressure definition.
4. Reliability framework.
5. Top 10 batters.
6. Top 10 bowlers.
7. Squad gaps and auction implications.
8. Limitations and data confidence.

Populate rankings or implications only after the required approvals, data-quality gates, sample decisions, and independent review. This draft does not contain the lists or recommendations.

## 9. Separate planning note: efficient reconciliation methods

This design note addresses the prior blocked runner only. The previous positional join used source-record numbers without a supporting index on the join fields. On two roughly 201,000-row sources, that can lead to repeated scans and work that grows toward a nested-loop comparison. The prior run is frozen as PARTIAL - BLOCKED; this note does not repair it, authorize another run, or infer any data result.

Candidate approaches for a separately authorized implementation:

1. **Stable composite-key index.** Parse both sources without coercion and index complete keys by the exact raw tuple (match_id, innings, innings_ball_num). Match only keys unique in both sources and with compatible documented types. Report duplicates, incomplete keys, and source-only keys separately. A keyed index improves lookup complexity but may require substantial memory or an explicitly approved disk-backed store.
2. **Chunked merge comparison.** If both sources are demonstrably ordered by the same key, a merge scan can compare rows with bounded memory. First validate ordering independently. If the inputs are not ordered consistently, do not silently sort or align by row number; any sorting or external storage requires an approved method and exact temporary/output paths.
3. **Hash-assisted matching.** A digest may narrow candidate matches or compare row fingerprints, but a hash is not a substitute for exact key/value verification. Compare raw fields after candidate selection, account for collision risk, and never use normalization to force a key match. Preserve ordered-key-sequence validation as a separate result.

Correctness controls for any approach: retain raw parsed values; document parser and type schema; do not coerce key types; do not pair duplicate or incomplete keys; separately record ordering differences, missing/additional columns, unmatched rows, and value changes; exclude ambiguous keys from matched-row counts; and preserve partial/interrupted evidence without overwriting.

Synthetic-only test-case definitions to consider before future implementation include: identical rows; reordered rows with stable keys; duplicate key on either side; missing key component; textual key difference such as leading zero; added, removed, and reordered columns; one changed value; row-count tail difference; quoted comma/newline and UTF-8 BOM; malformed field count; simulated digest collision requiring raw-value verification; large input with an indexed query plan; and interruption/no-overwrite behavior. These are planning examples only. No test code, fixtures, or tests were created or run.

## 10. Approval and status

This package is a planning draft only and is NOT APPROVED. It does not authorize data access, pressure analysis, metric calculation, rankings, modelling, or recommendations. All thresholds, metric readiness decisions, sample rules, validation choices, and output-use decisions remain open for explicit project-owner and technical review.