# Project Owner Authorization — Local IPL Data Processing

The project owner explicitly authorizes this application to read and process the competition data archive bundled at
`data/source/6af3166e7b922_data_pack.zip` for this project.

This owner decision removes the application's external trust-anchor-registry dependency for local project execution.
The application records the trust anchor as `NOT REQUIRED — OWNER-AUTHORIZED LOCAL PROJECT MODE`.

This is not a claim of independent security certification, external organizational approval, or third-party attestation.
Source archive/member hash checks, strict CSV parsing, source semantics checks, player-ID reconciliation,
data-quality exclusions, and ranking-methodology safeguards remain in force.

Automatic Top 10 outputs must still fail closed if pressure evidence, eligibility evidence, or a defensible
approved/versioned ranking methodology is absent. Owner authorization to process data is not itself methodology approval.
