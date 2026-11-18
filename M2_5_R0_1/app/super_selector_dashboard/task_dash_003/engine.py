"""Evidence-first batting and bowling aggregation interfaces.

The module consumes normalized, explicitly mapped evidence records. It does
not interpret source headers, classify pressure, calculate derived cricket
metrics, or rank players. Production mode is denied before input iteration.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import math
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping

# Reuse the immutable v0.1.5 authorization and scenario contracts from this
# code-only successor package. No files or data are loaded from production.
_V015_ROOT = Path(__file__).resolve().parents[1] / "versions" / "TASK_DASH_002_implementation_v0_1_5"
if str(_V015_ROOT) not in sys.path:
    sys.path.insert(0, str(_V015_ROOT))

from services.authorization import PRODUCTION_GATE
from services.scenario_registry import load_scenario_contracts


class CalculationInputError(ValueError):
    """Input cannot be safely attributed or separated into its declared scope."""


@dataclass(frozen=True)
class MeasureContract:
    """Caller-supplied mapping for an already normalized measure.

    `value_key` is not inferred by this module. The caller must map it only
    after source semantics and the measure definition have been approved.
    SUM is a generic reducer over supplied values, not a cricket metric rule.
    """

    measure_id: str
    value_key: str
    reducer: str
    dimension: str
    definition_ref: str
    source_semantics_ref: str


@dataclass(frozen=True)
class DimensionState:
    status: str
    value: None
    reason: str


@dataclass(frozen=True)
class CalculationResult:
    discipline: str
    status: str
    population: str
    ipl_measure_totals: Mapping[str, Mapping[str, Mapping[str, float | int]]]
    ipl_eligible_opportunity_counts: Mapping[str, int]
    historical_context: Mapping[str, Mapping[str, Mapping[str, Mapping[str, float | int]]]]
    historical_source_records: tuple[Mapping[str, Any], ...]
    historical_context_links: tuple[Mapping[str, Any], ...]
    historical_source_record_count: int
    historical_context_link_count: int
    evidence_trace: tuple[Mapping[str, Any], ...]
    scenario_evidence_counts: Mapping[str, Mapping[str, int]]
    scenario_contracts: tuple[Any, ...]
    effectiveness: DimensionState
    consistency: DimensionState
    reliability: DimensionState
    ranking_status: str
    limitations: tuple[str, ...]


_IPL_SEASONS = {"2022", "2023", "2024", "2025", "2026"}
_REQUIRED_TRACE = (
    "aggregation_grain",
    "player_id",
    "source_player_id",
    "canonical_player_id",
    "identity_mapping_ref",
    "identity_status",
    "competition_id",
    "canonical_competition_code",
    "competition_name",
    "competition_scope",
    "format",
    "season",
    "match_id",
    "event_id",
    "event_time",
    "source_record_refs",
)
_DIMENSIONS = {"effectiveness", "consistency", "reliability"}


def calculate_batting(
    records: Iterable[Mapping[str, Any]],
    *,
    measure_contracts: Iterable[MeasureContract],
    mode: str = "SYNTHETIC",
) -> CalculationResult:
    return _calculate("batting", records, measure_contracts=measure_contracts, mode=mode)


def calculate_bowling(
    records: Iterable[Mapping[str, Any]],
    *,
    measure_contracts: Iterable[MeasureContract],
    mode: str = "SYNTHETIC",
) -> CalculationResult:
    return _calculate("bowling", records, measure_contracts=measure_contracts, mode=mode)


def _calculate(
    discipline: str,
    records: Iterable[Mapping[str, Any]],
    *,
    measure_contracts: Iterable[MeasureContract],
    mode: str,
) -> CalculationResult:
    if discipline not in {"batting", "bowling"}:
        raise ValueError("discipline must be batting or bowling")
    if mode != "SYNTHETIC":
        PRODUCTION_GATE.require_production_authorization(f"run {discipline} calculation")

    contracts = _validate_measure_contracts(measure_contracts)
    scenarios = load_scenario_contracts()
    scenario_by_id = {item.scenario_id: item for item in scenarios}
    expected_prefix = "BAT-" if discipline == "batting" else "BWL-"

    ipl_totals: dict[str, dict[str, dict[str, float | int]]] = defaultdict(lambda: defaultdict(dict))
    opportunity_counts: dict[str, int] = defaultdict(int)
    history_totals: dict[str, dict[str, dict[str, dict[str, float | int]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    scenario_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    evidence_trace: list[Mapping[str, Any]] = []
    historical_source_records: list[Mapping[str, Any]] = []
    historical_context_links: list[Mapping[str, Any]] = []
    ipl_events: dict[str, list[tuple[Mapping[str, Any], datetime]]] = defaultdict(list)
    history: list[tuple[Mapping[str, Any], datetime]] = []
    seen_opportunities: set[str] = set()
    seen_grain_keys: set[tuple[str, ...]] = set()
    seen_source_refs: set[str] = set()

    # Fully validate/scope records before producing any output.
    for index, record in enumerate(records):
        _require_record_mapping(record, index)
        _require_trace(record, index)
        event_time = _parse_aware_time(record["event_time"], index)
        if record["identity_status"] != "RESOLVED":
            raise CalculationInputError(f"Record {index} has unresolved player identity.")
        if str(record["canonical_player_id"]) != str(record["player_id"]):
            raise CalculationInputError(f"Record {index} player_id does not match its resolved canonical_player_id.")
        if not str(record["identity_mapping_ref"]).strip():
            raise CalculationInputError(f"Record {index} lacks traceable player identity mapping.")
        if record["competition_scope"] == "IPL_RANKING":
            if str(record["canonical_competition_code"]).upper() != "IPL":
                raise CalculationInputError(f"Record {index} is marked IPL_RANKING but canonical competition code is not IPL.")
            if str(record["season"]) not in _IPL_SEASONS:
                continue  # Outside the owner-confirmed ranking population.
            _validate_unique_grain(record, discipline, index, seen_grain_keys, seen_source_refs)
            _require_scope_evidence(record, index)
            _validate_metric_values(record, contracts, index)
            _validate_scenario(record, scenario_by_id, expected_prefix, index)
            status = record.get("opportunity_status")
            if status == "ELIGIBLE":
                opportunity_id = record.get("opportunity_id")
                if not opportunity_id:
                    raise CalculationInputError(f"Eligible IPL record {index} lacks explicit opportunity_id.")
                key = f"{discipline}:{opportunity_id}"
                if key in seen_opportunities:
                    raise CalculationInputError(f"Duplicate eligible opportunity: {opportunity_id}")
                seen_opportunities.add(key)
            elif status not in {"INELIGIBLE", "NOT_AN_OPPORTUNITY"}:
                raise CalculationInputError(f"IPL record {index} has missing/unknown explicit opportunity_status.")
            ipl_events[str(record["player_id"])].append((record, event_time))
        elif record["competition_scope"] == "HISTORICAL_T20_CONTEXT":
            if str(record["canonical_competition_code"]).upper() == "IPL":
                raise CalculationInputError(f"Record {index} cannot label IPL as historical non-IPL context.")
            if record.get("identity_mapping_ref") is None or not str(record.get("identity_mapping_ref")).strip():
                raise CalculationInputError(f"Historical record {index} lacks traceable cross-competition identity mapping.")
            if "T20" not in str(record["format"]).upper():
                continue  # Non-T20 context is outside the owner-approved context scope.
            _validate_unique_grain(record, discipline, index, seen_grain_keys, seen_source_refs)
            _validate_metric_values(record, contracts, index)
            history.append((record, event_time))
        else:
            raise CalculationInputError(f"Record {index} has unknown competition_scope.")

    # IPL totals and denominators only use the owner-confirmed IPL population.
    for player_id, events in ipl_events.items():
        ipl_totals.setdefault(player_id, {})
        history_totals.setdefault(player_id, {})
        opportunity_counts[player_id] = 0
        for record, _event_time in events:
            evidence_trace.append(_trace_row(record, partition="IPL_RANKING"))
            if record.get("opportunity_status") == "ELIGIBLE":
                opportunity_counts[player_id] += 1
            for contract in contracts:
                value = record["measure_values"].get(contract.value_key)
                if value is None:
                    continue
                bucket = ipl_totals[player_id].setdefault(contract.dimension, {})
                bucket[contract.measure_id] = _reduce(bucket.get(contract.measure_id), value, contract.reducer)
            scenario_id = record.get("scenario_id")
            if scenario_id:
                scenario_counts[player_id][str(scenario_id)] += 1

    # Non-IPL context is attached only to the same resolved player and only
    # when strictly earlier than that player's evaluated IPL event. It is never
    # added to an IPL total or opportunity count.
    # Each accepted historical source record is represented once here. A
    # separate link is created for every evaluated IPL event it precedes.
    for row, _stamp in history:
        historical_source_records.append(_trace_row(row, partition="HISTORICAL_SOURCE_RECORD"))

    for player_id, events in ipl_events.items():
        player_history = [(row, stamp) for row, stamp in history if str(row["player_id"]) == player_id]
        for target, cutoff in events:
            target_event = str(target["event_id"])
            for row, stamp in player_history:
                if stamp >= cutoff:
                    continue
                link = _trace_row(row, partition="HISTORICAL_PRIOR_CONTEXT_LINK", evaluated_event_id=target_event)
                historical_context_links.append(link)
                evidence_trace.append(link)
                if not contracts:
                    continue
                comp_key = f"{row['competition_id']}|{row['format']}|{row['season']}|before:{target_event}"
                for contract in contracts:
                    value = row["measure_values"].get(contract.value_key)
                    output = history_totals[player_id].setdefault(comp_key, {}).setdefault(contract.dimension, {})
                    output[contract.measure_id] = _reduce(output.get(contract.measure_id), value, contract.reducer)

    # Preserve all scenario bindings exactly as loaded from the v0.2.2
    # authoritative registers; counts are evidence references, not labels.
    return CalculationResult(
        discipline=discipline,
        status="SYNTHETIC CALCULATION ONLY" if contracts else "SYNTHETIC EVIDENCE SUMMARY ONLY",
        population="IPL seasons 2022-2026; non-IPL T20 prior history kept separately",
        ipl_measure_totals={key: {dimension: dict(values) for dimension, values in dimensions.items()} for key, dimensions in ipl_totals.items()},
        ipl_eligible_opportunity_counts=dict(opportunity_counts),
        historical_context={key: {comp: {dimension: dict(values) for dimension, values in dimensions.items()} for comp, dimensions in groups.items()} for key, groups in history_totals.items()},
        historical_source_records=tuple(historical_source_records),
        historical_context_links=tuple(historical_context_links),
        historical_source_record_count=len(historical_source_records),
        historical_context_link_count=len(historical_context_links),
        evidence_trace=tuple(evidence_trace),
        scenario_evidence_counts={key: dict(value) for key, value in scenario_counts.items()},
        scenario_contracts=tuple(scenarios),
        effectiveness=DimensionState("NOT READY", None, "No approved effectiveness estimand is available; outputs are caller-defined observed-measure aggregates only."),
        consistency=DimensionState("NOT READY", None, "Consistency remains conceptual; no approved estimand or dependence treatment exists."),
        reliability=DimensionState("NOT READY", None, "No validated reliability score/composite is approved; evidence must remain separate."),
        ranking_status="NO-RANK",
        limitations=(
            "Synthetic inputs only; production mode is denied by the immutable Stage 2 gate.",
            "Measure values are caller-mapped normalized evidence; this engine does not infer source semantics or derive cricket metrics.",
            "Historical T20 context is prior-only, identity-mapped, competition-traceable and excluded from IPL totals/opportunity counts.",
            "Scenario contracts are preserved; this engine does not classify pressure events.",
            "No ranking formula, eligibility cutoff, uncertainty model or Top 10 selection is applied.",
        ) + (("No measure contracts supplied; measure totals and historical measure aggregates are intentionally empty.",) if not contracts else ()),
    )


def _validate_measure_contracts(contracts: Iterable[MeasureContract]) -> tuple[MeasureContract, ...]:
    result = tuple(contracts)
    ids: set[str] = set()
    for contract in result:
        if not isinstance(contract, MeasureContract):
            raise CalculationInputError("Every measure contract must be a MeasureContract.")
        if not contract.measure_id or not contract.value_key:
            raise CalculationInputError("Measure contracts require measure_id and value_key.")
        if contract.measure_id in ids:
            raise CalculationInputError(f"Duplicate measure_id: {contract.measure_id}")
        ids.add(contract.measure_id)
        if contract.reducer not in {"SUM"}:
            raise CalculationInputError("Only the explicit generic SUM reducer is implemented; no rate/score formula is inferred.")
        if contract.dimension not in _DIMENSIONS:
            raise CalculationInputError(f"Unknown output dimension: {contract.dimension}")
        if not contract.definition_ref or not contract.source_semantics_ref:
            raise CalculationInputError("Measure contract must cite definition and source-semantics references.")
    return result


def _require_record_mapping(record: Mapping[str, Any], index: int) -> None:
    if not isinstance(record, Mapping):
        raise CalculationInputError(f"Record {index} must be a mapping.")


def _require_trace(record: Mapping[str, Any], index: int) -> None:
    missing = [key for key in _REQUIRED_TRACE if key not in record or record[key] is None or record[key] == ""]
    if missing:
        raise CalculationInputError(f"Record {index} lacks traceability fields: {', '.join(missing)}")
    if not isinstance(record["source_record_refs"], (list, tuple)) or not record["source_record_refs"]:
        raise CalculationInputError(f"Record {index} requires at least one source_record_ref.")
    if not str(record.get("competition_scope_evidence_ref", "")).strip():
        raise CalculationInputError(f"Record {index} lacks competition scope evidence reference.")


def _validate_unique_grain(
    record: Mapping[str, Any],
    discipline: str,
    index: int,
    seen_grain_keys: set[tuple[str, ...]],
    seen_source_refs: set[str],
) -> None:
    """Enforce one normalized record per discipline/player/competition/match/event.

    The declared grain is `PLAYER_EVENT`: a calculation record represents one
    resolved player's single event in one match and competition. Source refs
    may include multiple supporting rows, but each ref can occur in only one
    accepted normalized record in the call.
    """
    if record["aggregation_grain"] != "PLAYER_EVENT":
        raise CalculationInputError(
            f"Record {index} declares unsupported aggregation_grain {record['aggregation_grain']!r}; expected 'PLAYER_EVENT'."
        )
    grain_key = (
        discipline,
        str(record["canonical_player_id"]),
        str(record["competition_id"]),
        str(record["match_id"]),
        str(record["event_id"]),
    )
    if grain_key in seen_grain_keys:
        raise CalculationInputError(f"Duplicate PLAYER_EVENT aggregation grain at record {index}: {grain_key}")
    refs = tuple(str(ref).strip() for ref in record["source_record_refs"])
    if not refs or any(not ref for ref in refs) or len(set(refs)) != len(refs):
        raise CalculationInputError(f"Record {index} has empty or repeated source_record_refs.")
    repeated = sorted(set(refs) & seen_source_refs)
    if repeated:
        raise CalculationInputError(f"Source evidence reused across normalized records at record {index}: {repeated}")
    seen_grain_keys.add(grain_key)
    seen_source_refs.update(refs)


def _require_scope_evidence(record: Mapping[str, Any], index: int) -> None:
    if not str(record.get("competition_scope_evidence_ref", "")).strip():
        raise CalculationInputError(f"Record {index} lacks owner/source evidence for IPL competition classification.")


def _validate_metric_values(record: Mapping[str, Any], contracts: tuple[MeasureContract, ...], index: int) -> None:
    if not contracts:
        return
    values = record.get("measure_values")
    if not isinstance(values, Mapping):
        raise CalculationInputError(f"Record {index} lacks normalized measure_values mapping.")
    for contract in contracts:
        if contract.value_key not in values:
            raise CalculationInputError(f"Record {index} lacks contracted measure value: {contract.value_key}")
        value = values[contract.value_key]
        if value is None:
            raise CalculationInputError(f"Record {index} has missing contracted measure value: {contract.value_key}; missingness rules are not inferred.")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise CalculationInputError(f"Record {index} has invalid numeric value for {contract.value_key}.")


def _validate_scenario(record: Mapping[str, Any], contracts: Mapping[str, Any], prefix: str, index: int) -> None:
    scenario_id = record.get("scenario_id")
    if scenario_id is None:
        return
    if scenario_id not in contracts:
        raise CalculationInputError(f"Record {index} references unknown scenario_id: {scenario_id}")
    if not str(scenario_id).startswith(prefix):
        raise CalculationInputError(f"Record {index} uses a scenario from the wrong discipline: {scenario_id}")


def _parse_aware_time(value: Any, index: int) -> datetime:
    if not isinstance(value, str):
        raise CalculationInputError(f"Record {index} event_time must be an ISO-8601 string with timezone.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CalculationInputError(f"Record {index} has invalid event_time.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CalculationInputError(f"Record {index} event_time must include timezone.")
    return parsed.astimezone(timezone.utc)


def _trace_row(record: Mapping[str, Any], *, partition: str, evaluated_event_id: str | None = None) -> Mapping[str, Any]:
    return {
        "partition": partition,
        "player_id": str(record["player_id"]),
        "source_player_id": str(record["source_player_id"]),
        "canonical_player_id": str(record["canonical_player_id"]),
        "identity_mapping_ref": str(record["identity_mapping_ref"]),
        "competition_id": str(record["competition_id"]),
        "competition_name": str(record["competition_name"]),
        "competition_scope": str(record["competition_scope"]),
        "format": str(record["format"]),
        "season": str(record["season"]),
        "match_id": str(record["match_id"]),
        "event_id": str(record["event_id"]),
        "event_time": str(record["event_time"]),
        "source_record_refs": tuple(str(x) for x in record["source_record_refs"]),
        "opportunity_id": record.get("opportunity_id"),
        "scenario_id": record.get("scenario_id"),
        "evaluated_event_id": evaluated_event_id,
    }


def _reduce(previous: float | int | None, value: float | int, reducer: str) -> float | int:
    if reducer != "SUM":
        raise CalculationInputError(f"Unsupported reducer: {reducer}")
    return value if previous is None else previous + value
