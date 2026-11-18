import csv
from pathlib import Path
import hashlib
import json

import pytest

from services.scenario_registry import load_scenario_contracts, load_scenario_registry, classify_with_contract
from services.research_layers import LAYER_NAMES, layer_states
from services.analysis_engines import prior_only_history, effectiveness, consistency, reliability, Stage2AuthorizationRequired
from services.metric_components import BATTER_METRICS, BOWLER_METRICS
from services.batting_engine import analyze_batting, batting_dimensions
from services.bowling_engine import analyze_bowling, bowling_dimensions
from services.authorization import PRODUCTION_GATE, ProductionExecutionDisabled
from services.ranking_engine import select_candidates, compare_candidates


def test_scenario_registers_are_exact_and_structured():
    rows = load_scenario_registry()
    contracts = load_scenario_contracts()
    assert len(rows) == len(contracts) == 18
    assert {x.scenario_id for x in contracts} == {f"BAT-S{i:02d}" for i in range(1, 10)} | {f"BWL-S{i:02d}" for i in range(1, 10)}
    for scenario in contracts:
        assert scenario.definition and scenario.match_situation and scenario.team_task
        assert scenario.individual_responsibility and scenario.eligible_opportunity_rule
        assert scenario.pre_event_fields and scenario.required_source_fields and scenario.baseline_requirement
        assert scenario.outcome_dimensions and scenario.attribution_requirements
        assert scenario.uncertainty_requirements and scenario.evidence_references
    assert {x.scenario_id for x in contracts if x.readiness_status == "DEFERRED"} == {"BAT-S03", "BWL-S04", "BWL-S08"}


def test_authoritative_scenario_wording_and_order_match_source_csvs():
    root = Path(__file__).resolve().parents[1] / "data" / "methodology"
    authoritative = []
    for name in ("BATTING_SCENARIO_REVIEW_v0_2_2.csv", "BOWLING_SCENARIO_REVIEW_v0_2_2.csv"):
        with (root / name).open(encoding="utf-8-sig", newline="") as stream:
            authoritative.extend(list(csv.DictReader(stream, strict=True)))
    mapped = {x.scenario_id: x for x in load_scenario_contracts()}
    assert len(authoritative) == 18
    assert all(mapped[r["Scenario ID"]].match_situation == r["Match situation"] for r in authoritative)
    assert all(mapped[r["Scenario ID"]].team_task == r["Team task"] for r in authoritative)
    assert all(mapped[r["Scenario ID"]].disposition == r["Disposition"] for r in authoritative)


def test_packaged_methodology_payloads_match_formal_stage1_bound_manifest():
    root = Path(__file__).resolve().parents[1]
    method = root / "data" / "methodology"
    manifest = method / "SHA256_MANIFEST.txt"
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == "573a80fcd3dc89ec02ff2718a0294336e94724a77586e48461ce73be56593740"
    for line in manifest.read_text(encoding="ascii").splitlines():
        if not line or line.startswith("Manifest"):
            continue
        digest, size, name = line.split("  ", 2)
        payload = (method / name).read_bytes()
        assert len(payload) == int(size)
        assert hashlib.sha256(payload).hexdigest() == digest


def test_review_responses_are_not_promoted_to_independent_finding_closure():
    p = Path(__file__).resolve().parents[1] / "data" / "methodology" / "INDEPENDENT_REVIEW_RESPONSE_MATRIX_v0_1.csv"
    with p.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, strict=True))
    assert {r["Finding ID"] for r in rows} == {f"METH-REV-{i:03}" for i in range(1, 8)}
    assert all("confirmation required" in r["Further review required"].lower() for r in rows)
    approval = Path(__file__).resolve().parents[1] / "data" / "governance_reference" / "STAGE1_FORMAL_METHODOLOGY_APPROVAL_v0_1.md"
    approval_text = approval.read_text(encoding="utf-8-sig")
    assert "METH-REV-001 through METH-REV-004 and METH-REV-007 RESOLVED" in approval_text
    assert "METH-REV-005 and METH-REV-006 ACCEPTED LIMITATION" in approval_text
    verification = approval.with_name("STAGE1_APPROVAL_ATTACHMENT_VERIFICATION_REPORT.md").read_text(encoding="utf-8-sig")
    assert "follow-up review file was not located for an independent rehash" in verification


def test_owner_confirmed_archive_identity_is_preserved_as_metadata_only():
    root = Path(__file__).resolve().parents[1]
    p = root / "data" / "governance_reference" / "OWNER_CONFIRMED_SOURCE_MEMBER_MANIFEST_v0_1_3.json"
    source = json.loads(p.read_text(encoding="utf-8"))
    assert source["archive_path"] == r"D:\Super Selector\6af3166e7b922_data_pack.zip"
    assert source["archive_sha256"] == "a992ecd89b3f22c4d6bfdf5dc9faf767491f8199a6ec09c33ab347db675bd8e1"
    assert source["archive_size_bytes"] == 6143211
    assert not (root / "data" / "production").exists()


def test_prior_package_manifests_are_preserved_byte_identity():
    root = Path(__file__).resolve().parents[1] / "data" / "governance_reference"
    expected = {
        "TASK_DASH_002_v0_1_1_SHA256_MANIFEST.txt": "38ec7c56be1afc5aef096a5f6f5684fed587a55f0c0d873156574174001eb4bb",
        "TASK_DASH_002_v0_1_2_SHA256_MANIFEST.txt": "1d93936787792a7d02462d4976f564463f2e752a0977377918862211778e206e",
        "TASK_DASH_002_v0_1_3_SHA256_MANIFEST.txt": "95dc30d5542b1a254271298e89aa27e2d068db14598e5e1c922efad8ebc08d6f",
        "STAGE1_FORMAL_APPROVAL_SHA256_MANIFEST.txt": "e1e64c3336a3c11e97a695c4ef09a9c2fd655386463d76cfdbd47721359da362",
        "PRIOR_REAL_ANALYTICS_SPECIFICATION_SHA256_MANIFEST.txt": "60890b9d6c0b8473b4230318a399bc5fd06d12cf74a8fc70ba10a86b1947d2f8",
    }
    assert {p.name for p in root.glob("*MANIFEST.txt")} == set(expected)
    assert all(hashlib.sha256((root / name).read_bytes()).hexdigest() == digest for name, digest in expected.items())


def test_five_layers_are_separate_and_no_real_layer_is_marked_ready():
    assert len(LAYER_NAMES) == 5
    assert tuple(x.layer for x in layer_states()) == LAYER_NAMES
    assert all(x.state == "NOT READY" for x in layer_states())
    assert all(x.state == "ILLUSTRATIVE FIXTURE ONLY" for x in layer_states(synthetic=True))


def test_scenario_classifier_is_fail_closed_even_with_supplied_inputs():
    contract = load_scenario_contracts()[0]
    result = classify_with_contract(contract, source_semantics_validated=True, approved_rule=True, pre_event_state={"example": True})
    assert result["classification"] == "UNCLASSIFIED"
    assert result["readiness"] == "NOT READY"


def test_revised_target_without_verified_pre_event_history_stays_unclassified():
    contracts = {x.scenario_id: x for x in load_scenario_contracts()}
    for sid in ("BAT-S09", "BWL-S09"):
        result = classify_with_contract(contracts[sid], pre_event_state={"revised_target": None, "effective_time": None})
        assert result["classification"] == "UNCLASSIFIED"
    assert contracts["BWL-S08"].readiness_status == "DEFERRED"
    assert "comfortable" in contracts["BAT-S02"].match_situation.lower()


def test_prior_only_baseline_excludes_event_equal_time_future_and_other_competition():
    base = [
        {"event_id": "prior", "player_id": "p1", "competition": "IPL", "event_time": "2024-01-01T00:00:00Z"},
        {"event_id": "same", "player_id": "p1", "competition": "IPL", "event_time": "2024-01-02T00:00:00+00:00"},
        {"event_id": "current", "player_id": "p1", "competition": "IPL", "event_time": "2024-01-02T00:00:00Z"},
        {"event_id": "future", "player_id": "p1", "competition": "IPL", "event_time": "2024-01-03T00:00:00+00:00"},
        {"event_id": "t20i", "player_id": "p1", "competition": "T20I", "event_time": "2023-01-01T00:00:00Z"},
    ]
    result = prior_only_history(base, player_id="p1", competition="IPL", event_time="2024-01-02T00:00:00Z", event_id="current")
    assert [x["event_id"] for x in result] == ["prior"]
    extended = base + [{"event_id": "later-added", "player_id": "p1", "competition": "IPL", "event_time": "2030-01-01T00:00:00Z"}]
    assert prior_only_history(extended, player_id="p1", competition="IPL", event_time="2024-01-02T00:00:00Z", event_id="current") == result


@pytest.mark.parametrize("cutoff", ["2024-01-01T00:00:00", "bad-time"])
def test_baseline_rejects_naive_or_invalid_cutoff(cutoff):
    with pytest.raises(ValueError):
        prior_only_history([], player_id="p", competition="IPL", event_time=cutoff)


def test_baseline_rejects_missing_historical_time_for_matching_population():
    with pytest.raises(ValueError, match="no timestamp"):
        prior_only_history([{"player_id": "p", "competition": "IPL"}], player_id="p", competition="IPL", event_time="2025-01-01T00:00:00Z")


def test_effectiveness_consistency_and_reliability_are_separate_and_unscored():
    dims = [effectiveness(), consistency(), reliability()]
    assert [x.dimension for x in dims] == ["effectiveness", "consistency", "reliability"]
    assert all(x.status == "NOT READY" and x.value is None for x in dims)


def test_batting_bowling_components_do_not_share_outcome_contract():
    assert BATTER_METRICS == ("scoring_contribution", "batter_attributed_dismissals")
    assert BOWLER_METRICS == ("run_containment", "bowler_credit_wickets", "dot_ball_performance")
    assert analyze_batting([]).status == "NOT READY"
    assert analyze_bowling([]).status == "NOT READY"
    assert all(x.status == "NOT READY" for x in batting_dimensions().values())
    assert all(x.status == "NOT READY" for x in bowling_dimensions().values())
    assert "NOT FEASIBLE" in bowling_dimensions()["run_containment"].reason
    assert "bowler-run allocation" in bowling_dimensions()["run_containment"].reason


def test_production_gate_is_not_user_configurable_and_denies_io_calculation_ranking():
    assert PRODUCTION_GATE.may_read_production
    assert PRODUCTION_GATE.may_calculate
    assert PRODUCTION_GATE.may_rank
    with pytest.raises(ProductionExecutionDisabled):
        PRODUCTION_GATE.require_production_authorization("read archive")
    with pytest.raises(Stage2AuthorizationRequired, match="Project Owner Stage 2 decision is GRANTED"):
        select_candidates([], discipline="batting", mode="REAL")


def test_synthetic_ranking_is_no_rank_and_comparison_fails_closed():
    assert select_candidates([], discipline="batting", mode="SYNTHETIC").status == "NO-RANK"
    assert select_candidates([], discipline="bowling", mode="SYNTHETIC").status == "NO-RANK"
    assert compare_candidates({}, {}).status == "NOT READY"

