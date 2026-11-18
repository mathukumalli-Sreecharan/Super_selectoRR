"""Exact scenario register and structured research contracts; no live labeling."""
import csv
from pathlib import Path
from models.analytics import ScenarioContract

APP_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_ROOT = APP_ROOT / "data" / "methodology"
FILES = (
    REGISTRY_ROOT / "BATTING_SCENARIO_REVIEW_v0_2_2.csv",
    REGISTRY_ROOT / "BOWLING_SCENARIO_REVIEW_v0_2_2.csv",
)


def load_scenario_registry() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in FILES:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows.extend(dict(row) for row in csv.DictReader(stream))
    expected = {f"BAT-S{i:02d}" for i in range(1, 10)} | {f"BWL-S{i:02d}" for i in range(1, 10)}
    actual = {row.get("Scenario ID", "") for row in rows}
    if actual != expected or len(rows) != 18:
        raise ValueError(f"Scenario registry identity mismatch: {sorted(actual)}")
    return rows


def classify_scenario(*_args, **_kwargs) -> dict[str, str]:
    """Return a fail-closed state because operational rules/readiness are not approved."""
    return {
        "classification": "UNCLASSIFIED",
        "readiness": "NOT READY",
        "reason": "Operational task rules, event-time source semantics, and metric-specific approval are not complete.",
    }


def load_scenario_contracts() -> tuple[ScenarioContract, ...]:
    contracts = []
    for row in load_scenario_registry():
        sid = row["Scenario ID"]
        batting = sid.startswith("BAT-")
        discipline = "batting" if batting else "bowling"
        if sid in {"BAT-S03", "BWL-S04", "BWL-S08"}:
            readiness = "DEFERRED"
        else:
            readiness = "NOT READY — OPERATIONAL RULES/EVIDENCE PENDING"
        outcomes = ("scoring contribution", "batter-attributed dismissal") if batting else ("run containment", "bowler-credit wicket", "dot ball")
        attribution = ("individual batter attribution", "faced-ball eligibility", "dismissal taxonomy") if batting else ("legal delivery", "extras/run allocation", "bowler-credit taxonomy")
        contracts.append(ScenarioContract(
            scenario_id=sid,
            discipline=discipline,
            definition=row["Why pressure may or may not exist"],
            match_situation=row["Match situation"],
            team_task=row["Team task"],
            individual_responsibility=row["Individual responsibility"],
            candidate_observations=row["Relevant candidate observations"],
            required_source_fields=tuple(x.strip() for x in row["Unresolved data requirements"].split(";") if x.strip()),
            unresolved_data_requirements=row["Unresolved data requirements"],
            disposition=row["Disposition"],
            eligible_opportunity_rule=("Actual eligible individual batter event; no partnership credit." if batting else "Actual eligible delivery bowled by the player; assignment is not exposure."),
            pre_event_fields=tuple(x.strip() for x in row["Relevant candidate observations"].split(";") if x.strip()),
            baseline_requirement=("Prior-only same-player IPL baseline; comparable opportunity/role only if validated."),
            outcome_dimensions=outcomes,
            attribution_requirements=attribution,
            uncertainty_requirements=("Metric-specific sample, match/player dependence and validated uncertainty; no numeric floor selected." ,),
            readiness_status=readiness,
            evidence_references=(str(FILES[0] if batting else FILES[1]),),
        ))
    return tuple(contracts)


def classify_with_contract(_contract: ScenarioContract, *, source_semantics_validated: bool = False, approved_rule: bool = False, pre_event_state: dict | None = None) -> dict[str, str]:
    """Do not classify until source evidence and operational rules are validated."""
    if not source_semantics_validated or not approved_rule or not pre_event_state:
        return {"classification": "UNCLASSIFIED", "readiness": "NOT READY", "reason": "Source semantics, pre-event evidence or approved operational rule is missing."}
    return {"classification": "UNCLASSIFIED", "readiness": "METHODOLOGY VALIDATION PENDING", "reason": "Local IPL data processing is owner-authorized. This scenario remains unclassified until its operational definition, source-field requirements and metric rules are implemented and empirically validated."}
