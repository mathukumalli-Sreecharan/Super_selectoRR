"""All input records and archive members in this suite are explicitly synthetic."""

from __future__ import annotations

import hashlib
from io import BytesIO
import warnings
import zipfile

import pytest

from task_dash_006a.archive import ArchiveManifest, ArchiveValidationError, ExpectedMember, verify_archive_bytes
from task_dash_006a.contracts import CsvSchemaContract, SOURCE_SEMANTIC_CONTRACTS, semantic_readiness, validate_source_semantics
from task_dash_006a.identity_scope import validate_identity_and_scope
from task_dash_006a.pipeline import SyntheticArchive, validate_synthetic_archive
from task_dash_006a.reporting import FINDING_FIELDS, findings_csv
from task_dash_006a.sequence import strictly_prior_events, validate_delivery_order
from task_dash_006a.state_adapter import StateReconstructionBlocked, SyntheticValidationEvidence, reconstruct_synthetic_states
from task_dash_006a.structural import validate_csv_bytes
from services.authorization import ProductionExecutionDisabled


def synthetic_zip(members: list[tuple[str, bytes]]) -> bytes:
    output = BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in members:
                archive.writestr(name, content)
    return output.getvalue()


def manifest_for(payload: bytes, members: dict[str, bytes]) -> ArchiveManifest:
    return ArchiveManifest(
        hashlib.sha256(payload).hexdigest(),
        {name: ExpectedMember(len(content), hashlib.sha256(content).hexdigest()) for name, content in members.items()},
    )


def valid_scope_rows():
    matches = [{"match_id": "SYN-M1", "comp_id": "SYN-C1", "home_team_id": "SYN-T1", "away_team_id": "SYN-T2"}]
    competitions = [{"comp_id": "SYN-C1", "competition_code": "IPL", "season": "2022", "format": "T20"}]
    teams = [{"comp_id": "SYN-C1", "team_id": "SYN-T1"}, {"comp_id": "SYN-C1", "team_id": "SYN-T2"}]
    participation = [
        {"match_id": "SYN-M1", "team_id": "SYN-T1", "player_id": "SYN-P1", "participated": True},
        {"match_id": "SYN-M1", "team_id": "SYN-T1", "player_id": "SYN-P2", "participated": True},
        {"match_id": "SYN-M1", "team_id": "SYN-T2", "player_id": "SYN-P9", "participated": True},
    ]
    deliveries = [{
        "match_id": "SYN-M1", "innings_id": "SYN-M1-I1", "delivery_id": "SYN-D1",
        "batting_team_id": "SYN-T1", "bowling_team_id": "SYN-T2", "striker_id": "SYN-P1",
        "non_striker_id": "SYN-P2", "bowler_id": "SYN-P9",
    }]
    return deliveries, matches, competitions, teams, participation


def test_synthetic_archive_and_member_hashes_pass():
    member = b"id,value\nSYN-1,1\n"
    payload = synthetic_zip([("synthetic.csv", member)])
    verified = verify_archive_bytes(payload, manifest_for(payload, {"synthetic.csv": member}))
    assert verified.status == "PASS"
    assert verified.data_mode == "SYNTHETIC"
    assert verified.member_payloads["synthetic.csv"] == member


def test_synthetic_archive_hash_mismatch_fails_closed():
    payload = synthetic_zip([("synthetic.csv", b"x\n1\n")])
    manifest = ArchiveManifest("0" * 64, {"synthetic.csv": ExpectedMember(4, "0" * 64)})
    with pytest.raises(ArchiveValidationError, match="ARCHIVE_SHA256_MISMATCH"):
        verify_archive_bytes(payload, manifest)


def test_malformed_synthetic_archive_manifest_fails_explicitly():
    with pytest.raises(ArchiveValidationError, match="INVALID_EXPECTED_ARCHIVE_SHA256"):
        verify_archive_bytes(b"synthetic", ArchiveManifest("bad", {}))
    with pytest.raises(ArchiveValidationError, match="INVALID_EXPECTED_MEMBER_CONTRACT"):
        verify_archive_bytes(b"synthetic", ArchiveManifest("0" * 64, None))


def test_synthetic_archive_missing_additional_and_duplicate_members_fail():
    payload = synthetic_zip([("one.csv", b"x\n1\n")])
    with pytest.raises(ArchiveValidationError, match="MISSING_ARCHIVE_MEMBER"):
        verify_archive_bytes(payload, ArchiveManifest(hashlib.sha256(payload).hexdigest(), {"two.csv": ExpectedMember(4, "0" * 64)}))
    with pytest.raises(ArchiveValidationError, match="UNEXPECTED_ARCHIVE_MEMBER"):
        verify_archive_bytes(payload, ArchiveManifest(hashlib.sha256(payload).hexdigest(), {}))
    duplicated = synthetic_zip([("one.csv", b"x\n1\n"), ("one.csv", b"x\n2\n")])
    with pytest.raises(ArchiveValidationError, match="DUPLICATE_ARCHIVE_MEMBER"):
        verify_archive_bytes(duplicated, ArchiveManifest(hashlib.sha256(duplicated).hexdigest(), {"one.csv": ExpectedMember(4, "0" * 64)}))


@pytest.mark.parametrize("wrong_member", [
    ExpectedMember(99, hashlib.sha256(b"x\n1\n").hexdigest()),
    ExpectedMember(4, "0" * 64),
])
def test_synthetic_member_size_or_hash_mismatch_fails(wrong_member):
    member = b"x\n1\n"
    payload = synthetic_zip([("one.csv", member)])
    with pytest.raises(ArchiveValidationError, match="MEMBER_(SIZE|SHA256)_MISMATCH"):
        verify_archive_bytes(payload, ArchiveManifest(hashlib.sha256(payload).hexdigest(), {"one.csv": wrong_member}))


def test_synthetic_pipeline_checks_schema_after_member_identity():
    member = b"id,value\nSYN-1,3\n"
    payload = synthetic_zip([("synthetic.csv", member)])
    fixture = SyntheticArchive(
        "SYNTHETIC", payload, manifest_for(payload, {"synthetic.csv": member}),
        {"synthetic.csv": CsvSchemaContract("synthetic.csv", ("id", "value"), ("id",), ("id",), {"value": "nonnegative_integer"})},
        "SYNTHETIC:test_fixture",
    )
    result = validate_synthetic_archive(fixture)
    assert result.data_mode == "SYNTHETIC"
    assert result.archive.status == "PASS"
    assert result.archive_report.status == "PASS"
    assert result.structural_reports[0].status == "PASS"


def test_synthetic_pipeline_returns_reason_coded_archive_failure_report():
    payload = synthetic_zip([("synthetic.csv", b"id\nSYN-1\n")])
    fixture = SyntheticArchive("SYNTHETIC", payload, ArchiveManifest("0" * 64, {}), {}, "SYNTHETIC:bad_archive")
    run = validate_synthetic_archive(fixture)
    assert run.status == "FAIL" and run.archive is None
    assert run.archive_report.findings[0].reason_code == "ARCHIVE_SHA256_MISMATCH"
    assert run.archive_report.findings[0].data_mode == "SYNTHETIC"


def test_production_mode_is_denied_before_fixture_inspection():
    with pytest.raises(ProductionExecutionDisabled, match="Stage 2 NOT GRANTED"):
        validate_synthetic_archive(None, mode="PRODUCTION")


def test_unlabelled_fixture_is_rejected():
    with pytest.raises(ValueError, match="explicitly labelled SYNTHETIC"):
        validate_synthetic_archive(SyntheticArchive("PRODUCTION", b"", ArchiveManifest("", {}), {}, "ref"))


def test_synthetic_structural_valid_csv_passes_explicit_contract():
    contract = CsvSchemaContract("synthetic.csv", ("id", "count", "event_date", "event_time"), ("id",), ("id",), {
        "count": "nonnegative_integer", "event_date": "iso_date", "event_time": "aware_datetime",
    })
    report, rows = validate_csv_bytes(b"id,count,event_date,event_time\nSYN-1,2,2026-01-01,2026-01-01T10:00:00Z\n", contract, evidence_ref="SYNTHETIC:csv_valid")
    assert report.status == "PASS" and report.data_mode == "SYNTHETIC"
    assert rows[0]["count"] == "2"


@pytest.mark.parametrize(("payload", "reason"), [
    (b"\xff\xfe", "INVALID_UTF8"),
    (b"id,value\nSYN-1,1,extra\n", "ROW_WIDTH_MISMATCH"),
    (b"id,value\nSYN-1,\"unterminated\n", "CSV_PARSE_ERROR"),
    (b"wrong,value\nSYN-1,1\n", "HEADER_MISMATCH"),
    (b"id,value\n,1\n", "MISSING_REQUIRED_VALUE"),
    (b"id,value\nSYN-1,-1\n", "INVALID_EXPLICIT_TYPE"),
    (b"id,value\nSYN-1,nope\n", "INVALID_EXPLICIT_TYPE"),
    (b"id,value\nSYN-1,1\nSYN-1,2\n", "DUPLICATE_KEY"),
])
def test_synthetic_structural_failures_report_reason(payload, reason):
    contract = CsvSchemaContract("synthetic.csv", ("id", "value"), ("id",), ("id",), {"value": "nonnegative_integer"})
    report, _ = validate_csv_bytes(payload, contract, evidence_ref="SYNTHETIC:invalid_csv")
    assert report.status == "FAIL"
    assert reason in {finding.reason_code for finding in report.findings}
    assert all(f.data_mode == "SYNTHETIC" for f in report.findings)


def test_synthetic_nullable_values_require_explicit_contract():
    contract = CsvSchemaContract("synthetic.csv", ("id", "value"), ("id",), ("id",), {"value": "nonnegative_integer"}, ("value",))
    report, rows = validate_csv_bytes(b"id,value\nSYN-1,\n", contract, evidence_ref="SYNTHETIC:nullable")
    assert report.status == "PASS" and rows[0]["value"] == ""


def test_identity_and_ipl_scope_exact_ids_pass_without_name_matching():
    args = valid_scope_rows()
    report = validate_identity_and_scope(deliveries=args[0], matches=args[1], competitions=args[2], teams=args[3], participation=args[4])
    assert report.status == "PASS"
    assert report.data_mode == "SYNTHETIC"


def test_missing_player_identity_and_unmapped_participation_fail():
    deliveries, matches, competitions, teams, participation = valid_scope_rows()
    deliveries[0]["striker_id"] = ""
    deliveries[0]["bowler_id"] = "SYN-P-UNMAPPED"
    report = validate_identity_and_scope(deliveries=deliveries, matches=matches, competitions=competitions, teams=teams, participation=participation)
    codes = {finding.reason_code for finding in report.findings}
    assert "MISSING_ACTOR_OR_TEAM_ID" in codes
    assert "UNMAPPED_PARTICIPATION" in codes


def test_duplicate_participation_key_fails_without_deduplication():
    deliveries, matches, competitions, teams, participation = valid_scope_rows()
    participation.append(dict(participation[0]))
    report = validate_identity_and_scope(deliveries=deliveries, matches=matches, competitions=competitions, teams=teams, participation=participation)
    assert "DUPLICATE_PARTICIPATION_KEY" in {finding.reason_code for finding in report.findings}


def test_malformed_participation_flag_is_not_coerced():
    deliveries, matches, competitions, teams, participation = valid_scope_rows()
    participation[0]["participated"] = "true"
    report = validate_identity_and_scope(deliveries=deliveries, matches=matches, competitions=competitions, teams=teams, participation=participation)
    assert "INVALID_NORMALIZED_PARTICIPATION_FLAG" in {finding.reason_code for finding in report.findings}


def test_unmapped_competition_scoped_team_id_fails():
    deliveries, matches, competitions, teams, participation = valid_scope_rows()
    deliveries[0]["bowling_team_id"] = "SYN-T-UNKNOWN"
    report = validate_identity_and_scope(deliveries=deliveries, matches=matches, competitions=competitions, teams=teams, participation=participation)
    assert "UNMAPPED_DELIVERY_TEAM_ID" in {finding.reason_code for finding in report.findings}


def test_non_ipl_competition_is_explicitly_out_of_scope():
    deliveries, matches, competitions, teams, participation = valid_scope_rows()
    competitions[0]["competition_code"] = "T20I"
    report = validate_identity_and_scope(deliveries=deliveries, matches=matches, competitions=competitions, teams=teams, participation=participation)
    assert "OUT_OF_SCOPE_COMPETITION" in {finding.reason_code for finding in report.findings}


def test_duplicate_delivery_identity_and_missing_match_join_fail():
    deliveries, matches, competitions, teams, participation = valid_scope_rows()
    deliveries.append(dict(deliveries[0]))
    deliveries[-1]["match_id"] = "SYN-MISSING"
    report = validate_identity_and_scope(deliveries=deliveries, matches=matches, competitions=competitions, teams=teams, participation=participation)
    codes = {finding.reason_code for finding in report.findings}
    assert "DUPLICATE_DELIVERY_ID" in codes
    assert "UNMAPPED_MATCH_ID" in codes


def ordered_rows():
    return [
        {"match_id": "SYN-M1", "innings_id": "SYN-I1", "delivery_id": "SYN-D1", "delivery_seq": 1, "event_time": "2022-01-01T10:00:00Z"},
        {"match_id": "SYN-M1", "innings_id": "SYN-I1", "delivery_id": "SYN-D2", "delivery_seq": 2, "event_time": "2022-01-01T10:00:01Z"},
    ]


def test_deterministic_delivery_order_and_verified_timestamps_pass():
    report = validate_delivery_order(ordered_rows(), timestamp_semantics="VERIFIED")
    assert report.status == "PASS"


def test_ambiguous_or_nonmonotonic_delivery_order_fails():
    rows = ordered_rows()
    rows[1]["delivery_seq"] = 1
    report = validate_delivery_order(rows, timestamp_semantics="VERIFIED")
    assert {f.reason_code for f in report.findings} & {"AMBIGUOUS_DELIVERY_ORDER", "NON_MONOTONIC_DELIVERY_ORDER"}
    assert report.status == "FAIL"


@pytest.mark.parametrize("timestamp", ["not-a-time", "2022-01-01T10:00:00"])
def test_invalid_or_naive_timestamps_fail_when_semantics_declared(timestamp):
    rows = ordered_rows()
    rows[0]["event_time"] = timestamp
    report = validate_delivery_order(rows, timestamp_semantics="VERIFIED")
    assert "INVALID_OR_MISSING_EVENT_TIMESTAMP" in {f.reason_code for f in report.findings}
    assert report.status == "FAIL"


def test_timestamp_sequence_conflict_fails():
    rows = ordered_rows()
    rows[1]["event_time"] = "2022-01-01T09:59:59Z"
    report = validate_delivery_order(rows, timestamp_semantics="VERIFIED")
    assert "TIMESTAMP_SEQUENCE_CONFLICT" in {f.reason_code for f in report.findings}


def test_unverified_timestamps_are_not_verifiable_not_assumed_valid():
    report = validate_delivery_order(ordered_rows(), timestamp_semantics="UNVERIFIED")
    assert report.status == "PASS"  # sequence itself passes; timestamp feature is separately unresolved
    assert any(f.status == "NOT_VERIFIABLE" and f.reason_code == "EVENT_TIME_SEMANTICS_UNVERIFIED" for f in report.findings)


def test_prior_only_filter_excludes_equal_and_future_information():
    rows = [
        {"event_id": "SYN-PRIOR", "event_time": "2022-01-01T09:59:00Z"},
        {"event_id": "SYN-EQUAL", "event_time": "2022-01-01T10:00:00Z"},
        {"event_id": "SYN-FUTURE", "event_time": "2022-01-01T10:01:00Z"},
    ]
    prior, finding = strictly_prior_events(rows, evaluated_at="2022-01-01T10:00:00Z", timestamp_semantics="VERIFIED")
    assert finding is None
    assert [row["event_id"] for row in prior] == ["SYN-PRIOR"]


def test_prior_only_filter_refuses_unverified_or_malformed_time():
    rows = [{"event_time": "2022-01-01T09:00:00Z"}]
    prior, finding = strictly_prior_events(rows, evaluated_at="2022-01-01T10:00:00Z", timestamp_semantics="UNVERIFIED")
    assert prior == () and finding.reason_code == "EVENT_TIME_SEMANTICS_UNVERIFIED"
    prior, finding = strictly_prior_events([{"event_time": "bad"}], evaluated_at="2022-01-01T10:00:00Z", timestamp_semantics="VERIFIED")
    assert prior == () and finding.reason_code == "INVALID_HISTORY_TIMESTAMP"


def test_source_semantics_stay_unverified_and_no_derivation_is_invented():
    assert SOURCE_SEMANTIC_CONTRACTS
    for contract in SOURCE_SEMANTIC_CONTRACTS:
        assert contract.status == "UNVERIFIED"
        assert semantic_readiness(contract)["status"] == "NOT_VERIFIABLE"
        assert semantic_readiness(contract)["reason_code"] == "SOURCE_SEMANTICS_UNVERIFIED"
    report = validate_source_semantics()
    assert report.status == "NOT_VERIFIABLE"
    assert len(report.findings) == len(SOURCE_SEMANTIC_CONTRACTS)
    assert all(row.status == "NOT_VERIFIABLE" and row.data_mode == "SYNTHETIC" for row in report.findings)


def test_validation_findings_serialize_with_required_fields_and_synthetic_label():
    report = validate_delivery_order(ordered_rows(), timestamp_semantics="UNVERIFIED")
    import csv
    from io import StringIO
    rows = list(csv.DictReader(StringIO(findings_csv((report,)))))
    assert tuple(rows[0]) == FINDING_FIELDS
    assert rows[0]["reason_code"] == "EVENT_TIME_SEMANTICS_UNVERIFIED"
    assert rows[0]["data_mode"] == "SYNTHETIC"


def test_state_adapter_requires_all_synthetic_validation_gates():
    evidence = SyntheticValidationEvidence("PASS", "PASS", "PASS", "NOT_VERIFIABLE", "PASS")
    with pytest.raises(StateReconstructionBlocked, match="NOT_VALIDATED"):
        reconstruct_synthetic_states(evidence, {}, [])


def test_synthetic_state_adapter_reuses_004b_pre_event_interface():
    evidence = SyntheticValidationEvidence("PASS", "PASS", "PASS", "PASS", "PASS")
    context = {
        "match_id": "SYN-M1", "innings_id": "SYN-M1-I2", "innings_type": "SECOND_INNINGS",
        "target": 10, "target_status": "VERIFIED", "target_source_ref": "SYNTHETIC:target",
        "legal_ball_semantics_status": "VERIFIED", "innings_legal_ball_limit": 12,
    }
    deliveries = [{
        "delivery_seq": 1, "delivery_id": "SYN-D1", "striker_id": "SYN-P1", "non_striker_id": "SYN-P2",
        "bowler_id": "SYN-P9", "team_runs": 4, "wicket_fell": False, "legal_delivery": True,
        "source_refs": ["SYNTHETIC:row1"],
    }]
    states = reconstruct_synthetic_states(evidence, context, deliveries)
    assert states[0]["score_before"] == 0
    assert states[0]["runs_remaining_before"] == 10
    assert states[0]["pressure_classification"] == "NOT_CLASSIFIED"


def test_conflicting_wicket_state_is_rejected_by_existing_004b_interface():
    evidence = SyntheticValidationEvidence("PASS", "PASS", "PASS", "PASS", "PASS")
    context = {
        "match_id": "SYN-M1", "innings_id": "SYN-M1-I2", "innings_type": "SECOND_INNINGS",
        "target": 10, "target_status": "VERIFIED", "target_source_ref": "SYNTHETIC:target",
        "legal_ball_semantics_status": "VERIFIED", "innings_legal_ball_limit": 12,
    }
    delivery = {
        "delivery_seq": 1, "delivery_id": "SYN-D1", "striker_id": "SYN-P1", "non_striker_id": "SYN-P2",
        "bowler_id": "SYN-P9", "team_runs": 0, "wicket_fell": False, "wickets_lost_after": 1,
        "legal_delivery": True, "source_refs": ["SYNTHETIC:row1"],
    }
    with pytest.raises(ValueError, match="wickets_lost_after is inconsistent"):
        reconstruct_synthetic_states(evidence, context, [delivery])


def test_missing_legal_ball_semantics_remain_partial_not_guessed():
    evidence = SyntheticValidationEvidence("PASS", "PASS", "PASS", "PASS", "PASS")
    context = {
        "match_id": "SYN-M1", "innings_id": "SYN-M1-I2", "innings_type": "SECOND_INNINGS",
        "target": 10, "target_status": "VERIFIED", "target_source_ref": "SYNTHETIC:target",
        "legal_ball_semantics_status": "UNVERIFIED", "innings_legal_ball_limit": 12,
    }
    delivery = {
        "delivery_seq": 1, "delivery_id": "SYN-D1", "striker_id": "SYN-P1", "non_striker_id": "SYN-P2",
        "bowler_id": "SYN-P9", "team_runs": 0, "wicket_fell": False, "legal_delivery": True,
        "source_refs": ["SYNTHETIC:row1"],
    }
    state = reconstruct_synthetic_states(evidence, context, [delivery])[0]
    assert state["state_status"] == "PARTIAL"
    assert state["legal_balls_remaining_before"] is None
    assert "LEGAL_BALL_SEMANTICS_UNVALIDATED" in state["reason_codes"]


def test_ambiguous_revised_target_remains_not_classifiable():
    evidence = SyntheticValidationEvidence("PASS", "PASS", "PASS", "PASS", "PASS")
    context = {
        "match_id": "SYN-M1", "innings_id": "SYN-M1-I2", "innings_type": "SECOND_INNINGS",
        "target": 20, "target_status": "VERIFIED", "target_source_ref": "SYNTHETIC:original",
        "target_revision_history_status": "VERIFIED",
        "target_revisions": [
            {"effective_before_delivery_seq": 1, "target": 20, "source_ref": "SYNTHETIC:original"},
            {"effective_before_delivery_seq": 2, "target": 14, "source_ref": "SYNTHETIC:revision-a"},
            {"effective_before_delivery_seq": 2, "target": 12, "source_ref": "SYNTHETIC:revision-b"},
        ],
        "legal_ball_semantics_status": "VERIFIED", "innings_legal_ball_limit": 12,
    }
    delivery = {
        "delivery_seq": 1, "delivery_id": "SYN-D1", "striker_id": "SYN-P1", "non_striker_id": "SYN-P2",
        "bowler_id": "SYN-P9", "team_runs": 0, "wicket_fell": False, "legal_delivery": True,
        "source_refs": ["SYNTHETIC:row1"],
    }
    next_delivery = dict(delivery, delivery_seq=2, delivery_id="SYN-D2", source_refs=["SYNTHETIC:row2"])
    state = reconstruct_synthetic_states(evidence, context, [delivery, next_delivery])[1]
    assert state["state_status"] == "NOT_CLASSIFIABLE"
    assert "CONFLICTING_ACTIVE_TARGET_REVISIONS" in state["reason_codes"]


