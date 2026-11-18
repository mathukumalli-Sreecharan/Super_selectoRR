"""Typed contracts for research outputs; no estimators are implied by these types."""
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AnalysisResult:
    status: str
    discipline: str
    reasons: tuple[str, ...]
    outputs: tuple[Any, ...] = ()

    @property
    def reason(self) -> str:
        return " ".join(self.reasons)


@dataclass(frozen=True)
class OpportunityRecord:
    opportunity_id: str
    player_id: str
    match_id: str
    innings_id: str
    event_id: str
    scenario_id: str | None
    status: str
    opportunity_type: str
    source_refs: tuple[str, ...] = ()
    exclusion_reason: str | None = None


@dataclass(frozen=True)
class ScenarioContract:
    scenario_id: str
    discipline: str
    definition: str
    match_situation: str
    team_task: str
    individual_responsibility: str
    candidate_observations: str
    required_source_fields: tuple[str, ...]
    unresolved_data_requirements: str
    disposition: str
    eligible_opportunity_rule: str
    pre_event_fields: tuple[str, ...]
    baseline_requirement: str
    outcome_dimensions: tuple[str, ...]
    attribution_requirements: tuple[str, ...]
    uncertainty_requirements: tuple[str, ...]
    readiness_status: str
    evidence_references: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EvidenceReference:
    player_id: str
    match_id: str
    competition: str
    season: str
    innings: str
    delivery_reference: str | None
    scenario_id: str | None
    opportunity_id: str | None
    source_archive_sha256: str | None
    source_member: str | None
    source_record_reference: str | None
    calculation_version: str
    inclusion_status: str
    reason: str
    baseline_cutoff: str | None = None
    limitation: str | None = None
    player_responsibility: str | None = None
    pre_event_state: dict[str, Any] = field(default_factory=dict)
    observed_outcome: dict[str, Any] = field(default_factory=dict)
    baseline_reference: str | None = None
    attribution_decision: str | None = None
    exclusion_reason: str | None = None
    uncertainty_evidence: str | None = None
    reliability_evidence: str | None = None


@dataclass(frozen=True)
class DimensionAssessment:
    dimension: str
    status: str
    value: float | None
    reason: str
