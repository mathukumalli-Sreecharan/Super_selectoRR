"""Metric-level readiness record with the approved seven evidence gates."""
from dataclasses import dataclass

GATE_NAMES = (
    "source_provenance_integrity",
    "operational_definition",
    "attribution_denominator",
    "data_quality_coverage",
    "leakage_prevention",
    "statistical_validity_uncertainty",
    "independent_verification",
)
EVIDENCE_ELEMENTS = (
    "metric identifier and operational definition",
    "source identity and provenance",
    "attribution and denominator validation",
    "data quality and coverage",
    "leakage prevention and event-time cutoffs",
    "estimator and uncertainty treatment",
    "validation evidence and tests",
    "independent reviewer and outcome",
    "limitations and permitted use",
    "analyst and owner decision/sign-off",
    "NO-RANK or INCONCLUSIVE result when evidence is insufficient",
)


@dataclass(frozen=True)
class MetricReadiness:
    metric_id: str
    status: str
    gate_results: dict[str, str]
    permitted_use: str
    limitation: str

    def validate(self) -> None:
        if self.status not in {"READY", "READY WITH LIMITATIONS", "NOT READY"}:
            raise ValueError(f"Invalid readiness status: {self.status}")
        if set(self.gate_results) != set(GATE_NAMES):
            raise ValueError("Every metric readiness record must include all seven gates.")
        allowed = {"PASS", "PASS WITH LIMITATIONS", "FAIL", "NOT EVIDENCED"}
        if any(result not in allowed for result in self.gate_results.values()):
            raise ValueError("Every gate must use a documented evidence state.")
        if self.status == "READY" and any(result != "PASS" for result in self.gate_results.values()):
            raise ValueError("READY requires every readiness gate to pass.")
        if self.status == "READY WITH LIMITATIONS" and any(result not in {"PASS", "PASS WITH LIMITATIONS"} for result in self.gate_results.values()):
            raise ValueError("READY WITH LIMITATIONS still requires evidence for every gate.")
        if self.permitted_use == "RANKING":
            raise ValueError("Metric readiness does not itself authorize player ranking.")


def blocked_metric(metric_id: str, reason: str) -> MetricReadiness:
    return MetricReadiness(
        metric_id=metric_id,
        status="NOT READY",
        gate_results={name: "NOT EVIDENCED" for name in GATE_NAMES},
        permitted_use="NO-RANK",
        limitation=reason,
    )
