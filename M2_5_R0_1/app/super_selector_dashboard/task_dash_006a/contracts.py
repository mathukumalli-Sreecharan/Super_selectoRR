"""Explicit schema/semantic contracts; unknown provider meanings stay unknown."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .reporting import ValidationFinding, ValidationReport


@dataclass(frozen=True)
class CsvSchemaContract:
    member_name: str
    headers: tuple[str, ...]
    required_nonempty: tuple[str, ...] = ()
    key_fields: tuple[str, ...] = ()
    # Rules are declared by a schema owner; this module never guesses them.
    type_rules: Mapping[str, str] | None = None
    nullable_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class SemanticContract:
    concept: str
    candidate_fields: tuple[str, ...]
    status: str
    evidence_required: str
    affected_scenarios: tuple[str, ...] = ()


# These are evidence gates, not provider definitions or derivation rules.
SOURCE_SEMANTIC_CONTRACTS = (
    SemanticContract("team_runs_and_extras", ("runs", "extras_type", "extras1_runs", "extras_2_runs"), "UNVERIFIED", "Attributable provider definitions and class-wise reconciliation."),
    SemanticContract("batter_runs", ("runs", "extras_type", "extras1_runs", "extras_2_runs"), "UNVERIFIED", "Provider definition separating batter runs from team total and extras."),
    SemanticContract("balls_faced", (), "UNVERIFIED", "Authoritative field or rule, exclusions and complete class coverage."),
    SemanticContract("legal_deliveries", (), "UNVERIFIED", "Authoritative field or rule, exceptions and complete class reconciliation.", ("BAT-S01", "BAT-S05", "BAT-S09", "BWL-S01", "BWL-S02", "BWL-S03", "BWL-S05", "BWL-S09")),
    SemanticContract("dismissals", ("is_wicket", "dismissal_type_id", "dismissal_type", "dismissed_player_id"), "UNVERIFIED", "Complete dismissal taxonomy and dismissed-player/opportunity rules."),
    SemanticContract("bowler_credit_wickets", ("bowler_id", "is_wicket", "dismissal_type_id", "dismissal_type", "dismissed_player_id"), "UNVERIFIED", "Class-specific bowler-credit taxonomy and population coverage."),
    SemanticContract("bowler_conceded_runs", ("runs", "extras_type", "extras1_runs", "extras_2_runs"), "UNVERIFIED", "Run allocation for all extras/dismissal classes and full-population reconciliation."),
    SemanticContract("target_and_revised_target_history", ("revised_target", "first_inn_revised_overs", "second_inn_revised_overs", "delivery_ist_time"), "UNVERIFIED", "Verified target/resource timeline with event-effective time and revision sequence.", ("BAT-S09", "BWL-S09")),
    SemanticContract("delivery_timestamp_and_order", ("innings", "overid", "over_ball_num", "innings_ball_num", "delivery_ist_time"), "UNVERIFIED", "Provider timestamp meaning/timezone plus deterministic event order and corrections."),
    SemanticContract("identity_and_participation", ("match_id", "comp_id", "team_id", "player_id", "is_played", "is_impact", "is_impact_off"), "UNVERIFIED", "Identifier namespace, continuity, participation/substitution and duplicate-key rules."),
)


def semantic_readiness(contract: SemanticContract, *, evidence_ref: str | None = None) -> dict[str, str]:
    """Return a fail-closed readiness result without deriving source meaning."""
    if contract.status != "VERIFIED" or not evidence_ref or not evidence_ref.strip():
        return {
            "status": "NOT_VERIFIABLE",
            "reason_code": "SOURCE_SEMANTICS_UNVERIFIED",
            "disposition": "Preserve as unresolved; do not derive or calculate.",
        }
    # A validated provider contract still needs a separate, reviewed checker.
    return {
        "status": "NOT_VERIFIABLE",
        "reason_code": "SEMANTIC_VALIDATOR_NOT_IMPLEMENTED",
        "disposition": "Bind an approved semantic validator before evaluating records.",
    }


def validate_source_semantics(*, evidence_refs: Mapping[str, str] | None = None) -> ValidationReport:
    """Emit structured evidence gates; never infer or mark source semantics PASS."""
    evidence_refs = evidence_refs or {}
    findings = []
    for contract in SOURCE_SEMANTIC_CONTRACTS:
        result = semantic_readiness(contract, evidence_ref=evidence_refs.get(contract.concept))
        findings.append(ValidationFinding(
            "SOURCE_SEMANTICS", contract.concept, result["status"], result["reason_code"],
            evidence_refs.get(contract.concept, "SYNTHETIC:semantic_contract"),
            ";".join(contract.affected_scenarios), result["disposition"],
        ))
    return ValidationReport("SOURCE_SEMANTICS", "NOT_VERIFIABLE", tuple(findings))
