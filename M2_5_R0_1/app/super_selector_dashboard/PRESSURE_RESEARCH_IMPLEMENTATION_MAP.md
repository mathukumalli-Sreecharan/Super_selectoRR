# Pressure analytics implementation map

The project receives real archive data through `services/production_loader.py`, which validates the pinned archive and CSV member hashes. `services/pressure_product.py` now filters the five exact IPL competitions, reconciles delivery attribution, reconstructs pre/post state, classifies B1–B10 and W1–W6 candidate situations, computes prior-only player baselines, produces provisional pressure orderings, performs coverage/pressure/season sensitivity runs, and writes the reproducible exports. `pages/dashboard.py` exposes the resulting research views and evidence explorer.

| Area | Status | Evidence / limitation |
|---|---|---|
| Supplied source and IPL 2022–2026 population | Implemented | Exact competition names and IDs; archive/member hashes verified. |
| Delivery scoring and state reconstruction | Partial, source exceptions exposed | 302 IPL rows have unresolved run/extras semantics; later states in affected innings are marked partial. |
| Pre-delivery chronology and time-safe personal baselines | Implemented | Current delivery outcome never enters its pre-state; cumulative player baseline is shifted one delivery and sorted by source timestamp. |
| Scenario classification | Provisional implementation | B1–B10 and W1–W6 are separately tagged. B2 role, B6 resource contrasts, match closeness/stakes, and some responsibility signals remain limited by source evidence. |
| Automatic player orderings | Provisional observational orderings | No composite score. The order uses pressure outcome versus prior-only player baseline, then coverage and matches. Eligibility floors are provisional and sensitivity is exported. |
| Reliability, consistency, uncertainty | Partial | Coverage labels and match/season dispersion are shown. Clustered intervals and hierarchical estimates are not implemented. |
| Streamlit application and exports | Implemented | Fourteen research views, source evidence explorer, and required CSV/JSON exports. |

Implemented parameter choices are research recommendations, not formal methodology approval. See `data/exports/methodology_configuration.json` and `data/exports/data_quality_report.csv` for run-specific definitions and exclusions.
