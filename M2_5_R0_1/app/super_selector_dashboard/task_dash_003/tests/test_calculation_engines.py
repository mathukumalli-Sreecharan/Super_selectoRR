from copy import deepcopy

import pytest

from services.authorization import ProductionExecutionDisabled
from services.scenario_registry import load_scenario_contracts
from task_dash_003.engine import (
    CalculationInputError,
    MeasureContract,
    calculate_batting,
    calculate_bowling,
)


def measure(discipline="batting"):
    return [MeasureContract(
        measure_id=f"{discipline}_fixture_observation",
        value_key="fixture_value",
        reducer="SUM",
        dimension="effectiveness",
        definition_ref="SYNTHETIC-TEST-ONLY",
        source_semantics_ref="SYNTHETIC-TEST-ONLY",
    )]


def record(*, player="p1", competition="IPL", scope="IPL_RANKING", season=2024,
           event="ipl-1", time="2024-06-01T12:00:00Z", value=4,
           opportunity="ELIGIBLE", opportunity_id="opp-1", scenario="BAT-S01",
           discipline="batting", identity="RESOLVED", mapping_ref=None):
    row = {
        "aggregation_grain": "PLAYER_EVENT",
        "player_id": player,
        "source_player_id": f"source-{player}",
        "canonical_player_id": player,
        "identity_mapping_ref": mapping_ref if mapping_ref is not None else "SYNTHETIC-IDENTITY-MAP",
        "identity_status": identity,
        "competition_id": competition,
        "canonical_competition_code": "IPL" if scope == "IPL_RANKING" else competition,
        "competition_name": competition,
        "competition_scope": scope,
        "competition_scope_evidence_ref": "SYNTHETIC-SCOPE-MAP",
        "format": "T20",
        "season": str(season),
        "match_id": f"match-{event}",
        "event_id": event,
        "event_time": time,
        "source_record_refs": [f"SYNTHETIC:{event}"],
        "measure_values": {"fixture_value": value},
        "opportunity_status": opportunity,
        "opportunity_id": opportunity_id,
        "scenario_id": scenario,
    }
    if scope == "HISTORICAL_T20_CONTEXT":
        row["identity_mapping_ref"] = mapping_ref if mapping_ref is not None else "SYNTHETIC-IDENTITY-MAP"
        row.pop("opportunity_status")
        row.pop("opportunity_id")
        row.pop("scenario_id")
    return row


def test_batting_engine_aggregates_only_ipl_and_keeps_t20_history_separate():
    rows = [
        record(event="ipl-1", value=10, opportunity_id="bat-1", scenario="BAT-S01"),
        record(event="domestic-prior", competition="DOMESTIC-1", scope="HISTORICAL_T20_CONTEXT",
               season=2023, time="2023-05-01T12:00:00Z", value=7),
        record(event="t20i-future", competition="T20I-1", scope="HISTORICAL_T20_CONTEXT",
               season=2025, time="2025-05-01T12:00:00Z", value=99),
        record(event="other-player", player="p2", competition="T20I-1", scope="HISTORICAL_T20_CONTEXT",
               season=2023, time="2023-05-01T12:00:00Z", value=88),
        record(event="outside-ipl-scope", season=2021, value=100, opportunity_id="old-opp"),
    ]
    result = calculate_batting(rows, measure_contracts=measure("batting"))
    assert result.ipl_measure_totals == {"p1": {"effectiveness": {"batting_fixture_observation": 10}}}
    assert result.ipl_eligible_opportunity_counts == {"p1": 1}
    assert any(x["partition"] == "IPL_RANKING" and x["event_id"] == "ipl-1" for x in result.evidence_trace)
    assert any(x["partition"] == "HISTORICAL_PRIOR_CONTEXT_LINK" and x["event_id"] == "domestic-prior" for x in result.evidence_trace)
    assert not any(x["event_id"] == "t20i-future" for x in result.evidence_trace)
    context = result.historical_context["p1"]
    assert len(context) == 1
    assert next(iter(context.values())) == {"effectiveness": {"batting_fixture_observation": 7}}
    assert result.ranking_status == "NO-RANK"
    assert result.effectiveness.status == result.consistency.status == result.reliability.status == "NOT READY"
    assert len(result.scenario_contracts) == 18
    assert {x.scenario_id for x in result.scenario_contracts} == {x.scenario_id for x in load_scenario_contracts()}


def test_primary_ipl_population_includes_exactly_the_five_owner_confirmed_seasons():
    rows = [
        record(event=f"ipl-{year}", season=year, value=1, opportunity_id=f"opp-{year}", scenario="BAT-S01")
        for year in (2022, 2023, 2024, 2025, 2026)
    ]
    rows.append(record(event="future-season", season=2027, value=100, opportunity_id="opp-2027"))
    result = calculate_batting(rows, measure_contracts=measure())
    assert result.ipl_measure_totals["p1"]["effectiveness"]["batting_fixture_observation"] == 5
    assert result.ipl_eligible_opportunity_counts["p1"] == 5
    assert not any(item["event_id"] == "future-season" for item in result.evidence_trace)


def test_empty_measure_contracts_return_evidence_and_opportunities_without_aggregates():
    rows = [
        record(event="ipl-a", time="2024-06-01T12:00:00Z", opportunity_id="ipl-a"),
        record(event="ipl-b", time="2024-06-02T12:00:00Z", opportunity_id="ipl-b"),
        record(event="prior", competition="T20I-X", scope="HISTORICAL_T20_CONTEXT",
               time="2023-01-01T00:00:00Z", value=8),
    ]
    for row in rows:
        row.pop("measure_values")
    result = calculate_batting(rows, measure_contracts=[])
    assert result.status == "SYNTHETIC EVIDENCE SUMMARY ONLY"
    assert result.ipl_measure_totals == {"p1": {}}
    assert result.historical_context == {"p1": {}}
    assert result.ipl_eligible_opportunity_counts == {"p1": 2}
    assert result.scenario_evidence_counts["p1"] == {"BAT-S01": 2}
    assert result.historical_source_record_count == 1
    assert result.historical_context_link_count == 2
    assert len(result.historical_source_records) == 1
    assert len(result.historical_context_links) == 2
    assert {link["evaluated_event_id"] for link in result.historical_context_links} == {"ipl-a", "ipl-b"}
    assert all(link["event_id"] == "prior" for link in result.historical_context_links)


def test_bowling_engine_keeps_ipl_opportunities_independent_from_history():
    rows = [
        record(event="bwl-1", value=3, opportunity_id="bowl-1", scenario="BWL-S01"),
        record(event="bwl-2", value=5, opportunity_id="bowl-2", scenario="BWL-S02"),
        record(event="prior-league", competition="LEAGUE-X", scope="HISTORICAL_T20_CONTEXT",
               season=2023, time="2023-03-01T00:00:00Z", value=500),
    ]
    result = calculate_bowling(rows, measure_contracts=measure("bowling"))
    assert result.ipl_measure_totals == {"p1": {"effectiveness": {"bowling_fixture_observation": 8}}}
    assert result.ipl_eligible_opportunity_counts == {"p1": 2}
    assert len(result.historical_context["p1"]) == 2
    assert all(group["effectiveness"]["bowling_fixture_observation"] == 500 for group in result.historical_context["p1"].values())
    assert result.scenario_evidence_counts["p1"] == {"BWL-S01": 1, "BWL-S02": 1}
    assert result.ranking_status == "NO-RANK"


def test_future_historical_rows_are_excluded_using_timezone_aware_event_times():
    rows = [
        record(event="eval", time="2024-06-01T12:00:00+00:00", value=1, opportunity_id="eval-opp"),
        record(event="history-before", competition="T20I-X", scope="HISTORICAL_T20_CONTEXT",
               time="2024-06-01T11:59:59Z", value=2),
        record(event="history-equal", competition="T20I-X", scope="HISTORICAL_T20_CONTEXT",
               time="2024-06-01T12:00:00Z", value=3),
        record(event="history-after", competition="T20I-X", scope="HISTORICAL_T20_CONTEXT",
               time="2024-06-01T12:00:01Z", value=4),
    ]
    result = calculate_batting(rows, measure_contracts=measure())
    values = [v for group in result.historical_context["p1"].values() for dimension in group.values() for v in dimension.values()]
    assert values == [2]
    assert result.ipl_measure_totals["p1"]["effectiveness"]["batting_fixture_observation"] == 1


@pytest.mark.parametrize("change", [
    {"identity_status": "AMBIGUOUS"},
    {"player_id": ""},
    {"competition_scope_evidence_ref": ""},
    {"source_record_refs": []},
    {"event_time": "2024-01-01T00:00:00"},
])
def test_missing_or_unresolved_traceability_fails_closed(change):
    row = record()
    row.update(change)
    with pytest.raises(CalculationInputError):
        calculate_batting([row], measure_contracts=measure())


def test_cross_competition_identity_mapping_is_mandatory():
    row = record(event="history", competition="T20I", scope="HISTORICAL_T20_CONTEXT",
                 time="2023-01-01T00:00:00Z", mapping_ref="")
    with pytest.raises(CalculationInputError, match="identity_mapping_ref"):
        calculate_batting([record(), row], measure_contracts=measure())


def test_source_player_must_resolve_to_the_canonical_player_id():
    row = record()
    row["canonical_player_id"] = "different-player"
    with pytest.raises(CalculationInputError, match="does not match"):
        calculate_batting([row], measure_contracts=measure())


def test_invalid_competition_labels_and_scenario_drift_are_rejected():
    mislabeled = record(competition="T20I-X", scope="IPL_RANKING")
    mislabeled["canonical_competition_code"] = "T20I-X"
    with pytest.raises(CalculationInputError, match="canonical competition code"):
        calculate_batting([mislabeled], measure_contracts=measure())
    wrong_scenario = record(scenario="BWL-S01")
    with pytest.raises(CalculationInputError, match="wrong discipline"):
        calculate_batting([wrong_scenario], measure_contracts=measure())


def test_missing_contracted_measure_value_fails_instead_of_substituting():
    row = record()
    row["measure_values"] = {}
    with pytest.raises(CalculationInputError, match="lacks contracted measure"):
        calculate_batting([row], measure_contracts=measure())

    row["measure_values"] = {"fixture_value": None}
    with pytest.raises(CalculationInputError, match="missingness rules are not inferred"):
        calculate_batting([row], measure_contracts=measure())


def test_historical_opportunities_never_enter_ipl_denominator():
    row = record(event="hist", competition="DOMESTIC-X", scope="HISTORICAL_T20_CONTEXT",
                 time="2023-01-01T00:00:00Z")
    row["opportunity_status"] = "ELIGIBLE"
    row["opportunity_id"] = "history-only"
    result = calculate_batting([record(), row], measure_contracts=measure())
    assert result.ipl_eligible_opportunity_counts == {"p1": 1}


def test_production_gate_denies_before_iterating_or_reading_input():
    class ForbiddenInput:
        def __iter__(self):
            raise AssertionError("Production input must not be touched before authorization.")

    with pytest.raises(ProductionExecutionDisabled, match="Stage 2 NOT GRANTED"):
        calculate_batting(ForbiddenInput(), measure_contracts=measure(), mode="REAL")
    with pytest.raises(ProductionExecutionDisabled, match="Stage 2 NOT GRANTED"):
        calculate_bowling(ForbiddenInput(), measure_contracts=measure("bowling"), mode="REAL")


def test_dimensions_remain_separate_and_unscored():
    rows = [record()]
    contracts = [
        MeasureContract("effect_fixture", "fixture_value", "SUM", "effectiveness", "SYNTHETIC", "SYNTHETIC"),
        MeasureContract("consistency_fixture", "fixture_value", "SUM", "consistency", "SYNTHETIC", "SYNTHETIC"),
        MeasureContract("reliability_fixture", "fixture_value", "SUM", "reliability", "SYNTHETIC", "SYNTHETIC"),
    ]
    result = calculate_batting(rows, measure_contracts=contracts)
    facts = result.ipl_measure_totals["p1"]
    assert set(facts) == {"effectiveness", "consistency", "reliability"}
    assert all(list(measures.values()) == [4] for measures in facts.values())
    assert [result.effectiveness.status, result.consistency.status, result.reliability.status] == ["NOT READY"] * 3


def test_unknown_reducer_or_missing_contract_references_are_rejected():
    with pytest.raises(CalculationInputError, match="generic SUM"):
        calculate_batting([], measure_contracts=[MeasureContract("rate", "x", "MEAN", "effectiveness", "d", "s")])
    bad = MeasureContract("x", "x", "SUM", "effectiveness", "", "")
    with pytest.raises(CalculationInputError, match="definition and source-semantics"):
        calculate_batting([], measure_contracts=[bad])


def test_input_records_are_not_mutated():
    rows = [record()]
    original = deepcopy(rows)
    calculate_batting(rows, measure_contracts=measure())
    assert rows == original


def test_aggregation_grain_must_be_explicit_and_supported():
    missing = record()
    del missing["aggregation_grain"]
    with pytest.raises(CalculationInputError, match="aggregation_grain"):
        calculate_batting([missing], measure_contracts=measure())
    unsupported = record()
    unsupported["aggregation_grain"] = "DELIVERY"
    with pytest.raises(CalculationInputError, match="expected 'PLAYER_EVENT'"):
        calculate_batting([unsupported], measure_contracts=measure())


def test_duplicate_player_event_grain_fails_before_it_can_inflate_totals():
    original = record(value=4)
    duplicate = dict(original, measure_values={"fixture_value": 40}, source_record_refs=["SYNTHETIC:different-row"])
    with pytest.raises(CalculationInputError, match="Duplicate PLAYER_EVENT aggregation grain"):
        calculate_batting([original, duplicate], measure_contracts=measure())


def test_reused_source_reference_across_distinct_events_fails():
    first = record(event="event-a", value=4)
    second = record(event="event-b", value=40, opportunity_id="opp-b")
    second["source_record_refs"] = first["source_record_refs"]
    with pytest.raises(CalculationInputError, match="Source evidence reused"):
        calculate_batting([first, second], measure_contracts=measure())


def test_repeated_reference_within_one_observation_fails():
    row = record()
    row["source_record_refs"] = ["SYNTHETIC:ipl-1", "SYNTHETIC:ipl-1"]
    with pytest.raises(CalculationInputError, match="empty or repeated source_record_refs"):
        calculate_batting([row], measure_contracts=measure())
