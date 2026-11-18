# TASK-DASH-002 — Real IPL Analytics Blocker Resolution Specification v0.1.0

**Purpose:** implementation specification for a future, separately authorized successor to the synthetic/read-only v0.1.3 application. This package is planning only. It neither changes governance statuses nor authorizes production processing.

## Package contents

- `BLOCKER_RESOLUTION_MATRIX.csv` — status-preserving closure map for source/data issues, TASK-001.4, IMPL-006/007, all OQ-001–OQ-013 and PA-OQ-001–PA-OQ-016, and Stage 2 prerequisites.
- `CALCULATION_ENGINE_SPECIFICATION.md` — proposed real-analysis components, field contracts, batting/bowling estimands, metric boundaries, validation and release architecture.
- `SCENARIO_IMPLEMENTATION_MATRIX.csv` — the nine authoritative batting and nine bowling v0.2.2 scenarios, with pre-event conditions, source evidence, responsibility, baseline and disposition.
- `SOURCE_FIELD_CONTRACT.md` — source headers and what can/cannot be established from them, without assigning undocumented semantics.
- `SHA256_MANIFEST.txt` — hashes and byte sizes for the other package files.

## Authority and status

The binding methodological reference is TASK-METH-001 v0.2.2, formally **APPROVED WITH LIMITATIONS** for Stage 1 by `governance/STAGE1_FORMAL_APPROVAL_v0_1/STAGE1_FORMAL_METHODOLOGY_APPROVAL_v0_1.md`, bound to manifest SHA-256 `573a80fcd3dc89ec02ff2718a0294336e94724a77586e48461ce73be56593740`. Scenario IDs and wording are taken from its bound v0.2.2 batting and bowling registers. The approval does not approve operational thresholds, estimators, metric readiness or ranking.

The owner-confirmed archive identity is recorded in `outputs/STAGE2_PRODUCTION_SOURCE_INVENTORY_UPDATED_20261118/SOURCE_SELECTION_OWNER_CONFIRMATION_2026-11-18.md`. That source-selection decision is not provenance/completeness evidence or processing authority. Existing v0.1.3 source QA is referenced as a prior read-only QA record only; this task did not open the ZIP or parse production CSV rows.

**Carried-forward statuses (unchanged):** Stage 1 APPROVED WITH LIMITATIONS; Stage 2 NOT GRANTED; production execution NOT AUTHORIZED; TASK-001.4 PARTIAL — BLOCKED; DQF-001 OPEN; M2.6 NOT READY; IMPL-006/007 OPEN; OQ-001–OQ-013 OPEN; PA-OQ-001–PA-OQ-016 OPEN; 30-versus-26 UNRESOLVED; production trust-anchor registry EMPTY. IMPL-009's accepted closure is narrowly limited to the v0.4.4 preparation remediation.

## Build boundary

Implementation may be designed and developed against synthetic fixtures only. The production path must fail closed until the separately documented source, readiness, trust, code-identity, output-contract and Stage 2 gates close. A future implementer must not convert an unresolved row below into an assumption. See the matrix for per-item closure evidence and dependency owners.

The selected IPL 2022–2026 archive is not requested again. Remaining evidence is provider/release, intended-season/scope declaration, data dictionary (including identifier, event-time, run/extras, legal-ball, dismissal and bowler-credit semantics), source completeness confirmation, and named accountable source steward. The selected archive identity alone does not supply those facts.
