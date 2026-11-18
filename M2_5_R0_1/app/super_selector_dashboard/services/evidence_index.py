"""Build explicit synthetic trace links; unknown production evidence stays null."""
from models.analytics import EvidenceReference


def build_fixture_evidence_index(data: dict) -> tuple[EvidenceReference, ...]:
    players = {x["player_id"]: x for x in data.get("players", [])}
    matches = {x["match_id"]: x for x in data.get("matches", [])}
    events = {x["event_id"]: x for x in data.get("events", [])}
    opportunities = {x["opportunity_id"]: x for x in data.get("opportunities", [])}
    classes = {x["classification_id"]: x for x in data.get("scenario_classifications", [])}
    records = {x["source_record_id"]: x for x in data.get("source_records", [])}
    artifacts = {x["source_artifact_id"]: x for x in data.get("source_artifacts", [])}
    baselines = {x["baseline_version_id"]: x for x in data.get("baselines", [])}
    reliability = {x["reliability_assessment_id"]: x for x in data.get("reliability_assessments", [])}
    output = []
    for metric in data.get("metrics", []):
        opportunity_ids = metric.get("opportunity_refs", [])
        scenario_ids = metric.get("scenario_classification_refs", [])
        for source_id in metric.get("source_record_refs", []):
            record = records.get(source_id, {})
            event = next((e for e in events.values() if source_id in e.get("source_record_refs", [])), {})
            match = matches.get(event.get("match_id"), {})
            opp = next((opportunities[x] for x in opportunity_ids if x in opportunities), {})
            scenario = next((classes[x] for x in scenario_ids if x in classes), {})
            artifact = artifacts.get(record.get("source_artifact_id"), {})
            baseline = baselines.get(metric.get("baseline_version_id"), {})
            rel = reliability.get(metric.get("reliability_assessment_id"), {})
            player = players.get(metric.get("player_id"), {})
            output.append(EvidenceReference(
                player_id=str(metric.get("player_id", "UNRESOLVED")),
                match_id=str(event.get("match_id", "UNRESOLVED")),
                competition=str(match.get("competition", "UNRESOLVED")),
                season=str(match.get("season", "UNRESOLVED")),
                innings=str(event.get("innings_id", "UNRESOLVED")),
                delivery_reference=event.get("delivery_ref"),
                scenario_id=scenario.get("scenario_id"),
                opportunity_id=opp.get("opportunity_id"),
                source_archive_sha256=None,
                source_member=None,
                source_record_reference=record.get("source_locator"),
                calculation_version=str(metric.get("metric_version", "UNRESOLVED")),
                inclusion_status="SYNTHETIC FIXTURE ONLY — NOT A PRODUCTION INCLUSION DECISION",
                reason=str(metric.get("label", "Fixture evidence only")),
                baseline_cutoff=baseline.get("cutoff_time"),
                limitation="Synthetic fixture contains no production archive/member identity; no source inference or metric calculation.",
                player_responsibility=player.get("role_context"),
                pre_event_state={},
                observed_outcome={},
                baseline_reference=metric.get("baseline_version_id"),
                attribution_decision="Fixture links only; provider attribution semantics unresolved.",
                exclusion_reason=None,
                uncertainty_evidence=rel.get("uncertainty_text"),
                reliability_evidence=rel.get("limitations", [None])[0] if rel.get("limitations") else None,
            ))
    return tuple(output)
