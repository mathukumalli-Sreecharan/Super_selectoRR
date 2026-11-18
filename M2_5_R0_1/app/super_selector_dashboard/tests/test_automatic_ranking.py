from services.automatic_ranking import automatic_rank, RANKING_METHODOLOGY_VERSION


def _candidate(index, **changes):
    row = {
        "player_id": f"P{index}",
        "pressure_opportunities": 12,
        "evidence_status": "VALIDATED",
        "pressure_scenario_status": "CLASSIFIED",
    }
    row.update(changes)
    return row


def test_insufficient_candidates_never_manufacture_top_ten():
    result = automatic_rank([_candidate(1)], discipline="batting")
    assert result["status"] == "INSUFFICIENT EVIDENCE"
    assert result["ranked"] == []
    assert result["preliminary_evidence_screen_count"] == 1
    assert "not final eligibility" in result["reason"]


def test_ten_or_more_candidates_still_fail_closed_without_approved_methodology():
    result = automatic_rank([_candidate(i) for i in range(12)], discipline="batting")
    assert result["status"] == "METHODOLOGY NOT APPROVED"
    assert result["ranked"] == []
    assert result["next_candidates"] == []
    assert result["preliminary_evidence_screen_count"] == 12
    assert result["methodology_version"].endswith("UNAPPROVED")


def test_unclassified_pressure_evidence_is_excluded():
    candidates = [_candidate(i, pressure_scenario_status="UNCLASSIFIED") for i in range(12)]
    result = automatic_rank(candidates, discipline="batting")
    assert result["status"] == "INSUFFICIENT EVIDENCE"
    assert result["preliminary_evidence_screen_count"] == 0
    assert result["excluded_reason_counts"]["PRESSURE_SCENARIOS_NOT_CLASSIFIED"] == 12


def test_unvalidated_evidence_is_excluded_even_with_positive_opportunities():
    result = automatic_rank([_candidate(i, evidence_status="VALIDATED COVERAGE") for i in range(12)], discipline="bowling")
    assert result["preliminary_evidence_screen_count"] == 0
    assert result["excluded_reason_counts"]["PRESSURE_EVIDENCE_NOT_VALIDATED"] == 12


def test_boolean_opportunity_count_is_not_accepted_as_integer_evidence():
    result = automatic_rank([_candidate(i, pressure_opportunities=True) for i in range(12)], discipline="batting")
    assert result["preliminary_evidence_screen_count"] == 0
    assert result["excluded_reason_counts"]["NO_VALID_PRESSURE_OPPORTUNITIES"] == 12


def test_duplicate_and_missing_player_ids_are_excluded():
    candidates = [_candidate(1), _candidate(1), _candidate(2, player_id="")]
    result = automatic_rank(candidates, discipline="batting")
    assert result["preliminary_evidence_screen_count"] == 1
    assert result["excluded_reason_counts"]["DUPLICATE_PLAYER_ID"] == 1
    assert result["excluded_reason_counts"]["MISSING_PLAYER_ID"] == 1


def test_unknown_discipline_is_not_validated():
    result = automatic_rank([], discipline="other")
    assert result["status"] == "NOT VALIDATED"
    assert result["ranked"] == []
    assert result["methodology_version"] == RANKING_METHODOLOGY_VERSION


def test_empty_candidate_input_is_no_rank():
    result = automatic_rank([], discipline="batting")
    assert result["status"] == "NO-RANK"
    assert result["ranked"] == []
