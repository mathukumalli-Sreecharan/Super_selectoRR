import pytest

from services.fixture_store import load_fixture
from services.opportunity_engine import validate_opportunities, eligible_fixture_opportunities
from services.profiles import synthetic_profile
from services.traceability import evidence_chain
from services.comparison import compare_profiles
from services.evidence_index import build_fixture_evidence_index
from services.source_interpretation import interpret_delivery
from services.authorization import ProductionExecutionDisabled


def test_fixture_integrity_and_explicit_opportunity_ids():
    data = load_fixture()
    parsed = validate_opportunities(data["opportunities"], event_records=data["events"])
    assert len(parsed) == len(data["opportunities"])
    assert all(x.opportunity_id and x.player_id and x.match_id and x.event_id for x in parsed)
    assert len(eligible_fixture_opportunities(data["opportunities"], discipline="BAT", event_records=data["events"])) == 2
    assert len(eligible_fixture_opportunities(data["opportunities"], discipline="BWL", event_records=data["events"])) == 1


def test_opportunity_engine_rejects_missing_and_duplicate_identity():
    with pytest.raises(ValueError, match="lacks explicit evidence"):
        validate_opportunities([{"player_id": "p"}])
    row = {"opportunity_id": "o", "player_id": "p", "match_id": "m", "event_id": "e", "opportunity_status": "ELIGIBLE (SYNTHETIC)"}
    with pytest.raises(ValueError, match="duplicate opportunity IDs"):
        validate_opportunities([row, row])


def test_profile_and_traceability_are_explicitly_synthetic_and_linked():
    data = load_fixture()
    player = data["players"][0]["player_id"]
    profile = synthetic_profile(data, player)
    assert "Synthetic fixture profile only" in profile["limitations"]
    assert all(o.player_id == player for o in profile["opportunities"])
    chain = evidence_chain(data, data["decisions"][0]["decision_id"])
    assert chain and chain[0]["Resolution"] == "RESOLVED"
    trace = build_fixture_evidence_index(data)
    assert trace and all(x.source_archive_sha256 is None and x.source_member is None for x in trace)
    assert all("SYNTHETIC FIXTURE ONLY" in x.inclusion_status for x in trace)


def test_comparison_requires_same_discipline_and_ready_evidence():
    assert compare_profiles({"discipline": "BAT"}, {"discipline": "BWL"}).status == "NOT READY"
    assert compare_profiles({"discipline": "BAT"}, {"discipline": "BAT"}, comparable_scenario=True, metric_readiness="NOT READY").status == "NOT READY"


def test_synthetic_delivery_interpretation_requires_explicit_fields_and_real_mode_denies_before_access():
    data = load_fixture()
    fact = interpret_delivery(data["delivery_records"][0], mode="SYNTHETIC")
    assert fact.validation_label.startswith("SYNTHETIC FIXTURE ONLY")
    assert isinstance(fact.legal_ball, bool) and isinstance(fact.batter_faced, bool)
    nonlegal = dict(data["delivery_records"][0], legal_ball=False)
    nonlegal_fact = interpret_delivery(nonlegal, mode="SYNTHETIC")
    assert nonlegal_fact.legal_ball is False  # explicit fixture flag is retained, not converted into a metric denominator
    with pytest.raises(ProductionExecutionDisabled):
        interpret_delivery({}, mode="REAL")
    invalid = dict(data["delivery_records"][0], legal_ball=None)
    with pytest.raises(ValueError, match="explicit candidate fields"):
        interpret_delivery(invalid, mode="SYNTHETIC")
