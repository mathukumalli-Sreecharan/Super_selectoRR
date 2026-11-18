# SupeRR Selector IPL pressure research dashboard

The application reads the supplied archive at `data/source/6af3166e7b922_data_pack.zip` and filters IPL 2022–2026 by exact competition IDs. Archive and member hashes are data-integrity checks; local analysis has no authorization or trust-anchor dependency.

## Launch

From this directory:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The first page load validates the archive, reconstructs delivery states, calculates the provisional pressure analyses, and writes the reproducible CSV and JSON files under `data/exports/`.

## Research status

The dashboard includes automatic, provisional pressure orderings and a delivery evidence explorer. These are not formally approved rankings. Several source rows have unresolved extras semantics; see **Data Quality and Coverage**, `KNOWN_LIMITATIONS.md`, and `data/exports/methodology_configuration.json` before interpreting the results.
