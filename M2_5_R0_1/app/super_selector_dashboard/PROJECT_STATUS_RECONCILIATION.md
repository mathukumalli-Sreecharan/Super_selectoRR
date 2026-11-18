# Project Status Reconciliation — R0_8

**Supersedes conflicting Stage 2 / production-access statements carried forward in earlier R0_1–R0_7 reports and governance reference files.**

## Authoritative owner decision
- Project owner Stage 2 decision: **GRANTED**.
- Local execution: **ENABLED**.
- Supplied IPL source archive: **available in the project at `data/source/6af3166e7b922_data_pack.zip`**.
- Trust anchor / external certificate / authorization portal: **NOT REQUIRED** for this owner-authorized local project mode.
- Production-data access: **permitted locally**. Source archive and member hashes are integrity checks only; they are not authorization gates.

## What this decision does not establish
Owner permission to process the data does not itself validate cricket calculations, pressure scenario definitions, metric estimands, sample requirements, uncertainty methods or the final automatic ranking formula. These are analytical implementation and validation tasks, not authorization prerequisites.

## Current product capability
The active Streamlit path reads the bundled source archive directly and calculates conventional IPL descriptive leaderboards. Those are not pressure rankings. Pressure scenario classification and pressure-based Top 10 ranking remain incomplete until implemented and empirically validated. No final pressure Top 1 or Top 10 should be claimed before that work is complete.

## Project directory naming
The R0_7/R0_8 release archive contains the internal project directory `M2_5_R0_1`. This is the existing project's folder name inside the release package, not evidence that the release is missing.

## Supersession rule
Where older files state Stage 2 NOT GRANTED, production NOT AUTHORIZED, real-data UI LOCKED, trust-anchor registry EMPTY, or require separate trust-anchor provisioning, treat those statements as historical and superseded by this reconciliation for the active local product. Historical evidence files are retained for provenance and must not be used as current runtime controls.
