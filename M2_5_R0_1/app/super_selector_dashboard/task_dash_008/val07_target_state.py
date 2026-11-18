"""VAL-07: only explicit, effective target evidence; no external DLS reconstruction."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .validation_common import integer_value, result, row_exception


def validate_target_state(evidence: Sequence[Mapping[str, Any]]):
    vid = "VAL-07"
    issues = []
    available = 0
    for row in evidence:
        if row.get("target_mapping_status") != "VALIDATED":
            issues.append(row_exception(vid, "TARGET_FIELD_MAPPING_NOT_VALIDATED", "UNRESOLVED", row, expected_rule="Use only provider/owner-mapped target fields."))
            continue
        revision_required = row.get("revision_required")
        if type(revision_required) is not bool:
            issues.append(row_exception(vid, "TARGET_REVISION_STATE_UNKNOWN", "UNRESOLVED", row))
            continue
        if revision_required:
            target = integer_value(row.get("revised_target_runs"))
            valid = (
                type(target) is int and target > 0
                and row.get("revision_status") == "VERIFIED"
                and row.get("effective_before_delivery") is True
            )
            if not valid:
                issues.append(row_exception(vid, "ACTIVE_REVISED_TARGET_UNAVAILABLE", "UNRESOLVED", row, expected_rule="No original-target fallback; active revised target must be verified and effective before delivery."))
            else:
                available += 1
        else:
            target = integer_value(row.get("original_target_runs"))
            if type(target) is not int or target <= 0 or row.get("original_target_status") != "VERIFIED":
                issues.append(row_exception(vid, "ORIGINAL_TARGET_UNAVAILABLE", "UNRESOLVED", row))
            else:
                available += 1
    if not evidence:
        issues.append(row_exception(vid, "TARGET_EVIDENCE_NOT_PROVIDED", "UNRESOLVED", {}))
    return result(vid, evidence, issues, metrics={"target_rows_available": available})
