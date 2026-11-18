# TASK-METH-001 — Formal Stage 1 Methodology Approval v0.1

**Decision date:** 17 November 2026  
**Approval status:** **APPROVED WITH LIMITATIONS**  
**Approved methodology:** TASK-METH-001 — Consolidated Batting and Bowling Methodology v0.2.2  
**Base/predecessor:** v0.2.1  
**Stage 2 statistical implementation authorization:** **NOT GRANTED**

## 1. Formal project-owner decision

The project owner formally approves Stage 1 of TASK-METH-001 for the exact consolidated batting and bowling methodology package identified below, subject to the limitations and boundaries recorded in this approval.

This approval adopts the conceptual methodology and governance framework in the approved package for the next project phase. It does not assert that individual metrics are ready, that operational pressure classifications or statistical estimators have been validated, or that player comparisons and rankings may begin.

## 2. Exact approved package identity

| Item | Approved identity |
|---|---|
| Task | TASK-METH-001 |
| Package | Consolidated Batting and Bowling Methodology v0.2.2 |
| Base/predecessor | v0.2.1 |
| Package directory | `D:\Super Selector\M2_5_R0_1\governance\METHODOLOGY_DECISION_PREPARATION_v0_2_2\` |
| Manifest | `SHA256_MANIFEST.txt` |
| Final package manifest SHA-256 | `573a80fcd3dc89ec02ff2718a0294336e94724a77586e48461ce73be56593740` |

This approval is bound to the exact manifest hash above. Any change to a payload or the manifest creates a different package identity and is not covered by this approval unless separately reviewed and approved.

## 3. Independent review relied upon

The project owner considered the following independent review:

| Item | Identity |
|---|---|
| Review | TASK-METH-001 — Independent Follow-up Review Report v0.1 |
| Review date | 17 November 2026 |
| Review outcome | SUITABLE FOR STAGE 1 OWNER APPROVAL WITH LIMITATIONS |
| Review report SHA-256 | `7bedd0b383128d1c6ee54fdddbf40ff8fcb00b6e1e4c378d59d71a0268d2fe43` |
| Exact reviewed package manifest SHA-256 | `573a80fcd3dc89ec02ff2718a0294336e94724a77586e48461ce73be56593740` |

The review verified all ten package payloads against the manifest and found no blocking defect to Stage 1 approval with limitations. Its finding dispositions were: METH-REV-001 through METH-REV-004 and METH-REV-007 RESOLVED; METH-REV-005 and METH-REV-006 ACCEPTED LIMITATION.

## 4. Accepted methodology limitations

The project owner explicitly accepts the following two limitations as conditions of Stage 1 approval:

### 4.1 METH-REV-005 — Statistical dependence

The appropriate dependence structure and uncertainty treatment have not yet been operationally specified or validated. Future statistical specification must assess, as supported by the data and estimand:

- multiple deliveries within matches;
- repeated observations of the same player across matches;
- shared match conditions between players; and
- spell dependence.

No affected metric may pass the statistical-validity readiness gate or support player comparisons until its dependence treatment and uncertainty method have been specified, validated and independently reviewed. No estimator is approved by this Stage 1 decision.

### 4.2 METH-REV-006 — Pressure consistency

Pressure consistency remains a conceptual repeatability dimension, not an approved estimable metric. Before any consistency metric can be marked READY, its estimand, comparable-opportunity population, treatment of sampling noise, dependence structure, uncertainty method and validation plan must be specified and independently reviewed. Raw dispersion or low variance alone must not be treated as pressure consistency.

No consistency metric is approved for calculation or player comparison by this Stage 1 decision.

## 5. Additional review-evidence limitations disclosed

The independent follow-up report also disclosed the following evidence boundaries. They are recorded here for transparency and are not silently represented as re-performed verification:

1. The detached Stage 1 package-binding record was not supplied to the follow-up reviewer and was not independently inspected. This approval itself identifies the exact package version and manifest hash. Any detached binding record remains an identity aid only, not an approval instrument.
2. The predecessor v0.2.1 package was not supplied for byte-level regression comparison during the follow-up review. Preservation of predecessor files was therefore not independently re-performed in that review.
3. The original v0.2.1 independent review report was not re-read during the follow-up review; the follow-up reviewer assessed the seven finding descriptions from the response matrix and v0.2.2 supporting documents.

These limitations do not change the exact identity of the v0.2.2 package approved here. They must remain visible in the project evidence trail.

## 6. Scope of Stage 1 approval

This approval covers the conceptual methodology and approval framework in the exact v0.2.2 package, including:

- the five-layer batting and bowling methodology architecture;
- separate batting and bowling pressure definitions and outcomes;
- pre-event information and leakage safeguards;
- actual individual responsibility and exposure principles;
- prior-only player-specific baselines and the adopted IPL/T20I and role-comparability principles;
- separate effectiveness, consistency and evidence-reliability concepts;
- metric-by-metric readiness gates and the metric-level evidence record; and
- the documented scenario scope, including interrupted/revised-target cases subject to verified event-time information.

This approval does not approve any unvalidated operational threshold, estimator, composite score, metric calculation, metric readiness status or player-ranking method. PA-OQ-001 through PA-OQ-016 remain OPEN unless separately resolved with evidence and appropriate approval.

## 7. Data and governance restrictions preserved

The following restrictions and statuses remain in force:

- No production-data access, source reconciliation or statistical implementation is authorized by Stage 1 approval.
- The blocked TASK-001.4 run and its seven outputs must remain untouched; no rerun, repair, reuse or overwrite is authorized by this record.
- TASK-001.4 remains **PARTIAL — BLOCKED**.
- DQF-001 remains **OPEN**.
- M2.6 remains **NOT READY**.
- TASK-001.4 OQ-001 through OQ-013 remain **OPEN**.
- PA-OQ-001 through PA-OQ-016 remain **OPEN**.
- The 30-versus-26 discrepancy remains **UNRESOLVED**.
- Existing `playing_eleven` structural-key and source CSV-width findings remain as documented; no repair or readiness upgrade is inferred.
- No metric readiness status is upgraded by this approval.

## 8. Stage 2 — separate implementation authorization

**Stage 2 status: NOT GRANTED.**

A separate, explicit project-owner authorization is required before any production-data access, source reconciliation, metric calculation or execution. That authorization must identify and bind at minimum:

1. the formally approved methodology and exact implementation specification versions and hashes;
2. exact source input paths, byte sizes and SHA-256 hashes, including any archive-member procedure;
3. exact implementation code path and SHA-256 hash, plus reproducible dependencies/environment;
4. exact approved execution directory and permitted directory-creation targets;
5. permitted operations and exact output names/schemas, with exclusions;
6. required controlled/synthetic tests, acceptance criteria and independent verification;
7. stop conditions; and
8. evidence preservation, no-overwrite and manifest requirements.

Methodology approval, metric readiness, synthetic test results, a command-line flag, or this approval record does not constitute Stage 2 authorization.

## 9. Formal approval statement

**The project owner approves TASK-METH-001 — Consolidated Batting and Bowling Methodology v0.2.2 for Stage 1, WITH LIMITATIONS, bound to package manifest SHA-256 `573a80fcd3dc89ec02ff2718a0294336e94724a77586e48461ce73be56593740`, and subject to all restrictions and accepted limitations recorded in this document. Stage 2 statistical implementation authorization is NOT GRANTED.**

**Approval authority:** Project Owner  
**Approval conveyed:** Explicit project-owner instruction in the conversation on 17 November 2026  
**Record status:** Formal Stage 1 approval record — to be committed to the project's version-controlled governance directory without changing the approved v0.2.2 package.
