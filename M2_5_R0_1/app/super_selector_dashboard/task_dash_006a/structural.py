"""Explicit-contract CSV structure checks over caller-supplied bytes."""

from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import io

from .contracts import CsvSchemaContract
from .reporting import ValidationFinding, ValidationReport


def _type_valid(value: str, rule: str) -> bool:
    if rule == "string":
        return True
    if rule == "integer":
        return value.isascii() and value.isdigit()
    if rule == "nonnegative_integer":
        return value.isascii() and value.isdigit()
    if rule == "decimal":
        try:
            return Decimal(value).is_finite()
        except InvalidOperation:
            return False
    if rule == "iso_date":
        try:
            date.fromisoformat(value)
            return True
        except ValueError:
            return False
    if rule == "aware_datetime":
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.tzinfo is not None and parsed.utcoffset() is not None
        except ValueError:
            return False
    if rule == "boolean_true_false":
        return value in {"true", "false"}
    raise ValueError(f"Unsupported explicit type rule: {rule}")


def validate_csv_bytes(
    payload: bytes,
    contract: CsvSchemaContract,
    *,
    evidence_ref: str,
    affected_scenarios: tuple[str, ...] = (),
) -> tuple[ValidationReport, tuple[dict[str, str], ...]]:
    findings: list[ValidationFinding] = []
    scenario_text = ";".join(affected_scenarios)
    def add(ref: str, code: str, disposition: str) -> None:
        findings.append(ValidationFinding("STRUCTURAL", ref, "FAIL", code, evidence_ref, scenario_text, disposition))
    try:
        text = payload.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError:
        add(contract.member_name, "INVALID_UTF8", "Quarantine member; do not replace or repair bytes silently.")
        return ValidationReport("STRUCTURAL", "FAIL", tuple(findings)), ()
    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = next(reader)
        if len(header) != len(set(header)):
            add(contract.member_name, "DUPLICATE_HEADER", "Reject schema until a versioned contract resolves duplicate names.")
        if tuple(header) != contract.headers:
            add(contract.member_name, "HEADER_MISMATCH", "Quarantine member; compare with the bound schema contract.")
        if not header:
            add(contract.member_name, "EMPTY_HEADER", "Reject empty CSV member.")
            return ValidationReport("STRUCTURAL", "FAIL", tuple(findings)), ()
        rows: list[dict[str, str]] = []
        row_num = 1
        for fields in reader:
            row_num += 1
            if len(fields) != len(header):
                add(f"{contract.member_name}:row:{row_num}", "ROW_WIDTH_MISMATCH", "Quarantine malformed row; never pad or truncate.")
                continue
            row = dict(zip(header, fields, strict=True))
            rows.append(row)
            for field in contract.required_nonempty:
                if field not in row:
                    add(f"{contract.member_name}:row:{row_num}", "CONTRACT_FIELD_MISSING", "Correct the explicit schema contract before validation.")
                elif row[field] == "":
                    add(f"{contract.member_name}:row:{row_num}:{field}", "MISSING_REQUIRED_VALUE", "Preserve missingness and quarantine or report per the approved contract.")
            for field, rule in (contract.type_rules or {}).items():
                if field not in row:
                    add(f"{contract.member_name}:row:{row_num}:{field}", "CONTRACT_FIELD_MISSING", "Correct the explicit schema contract before validation.")
                elif row[field] == "" and field in contract.nullable_fields:
                    continue
                elif row[field] == "" or not _type_valid(row[field], rule):
                    add(f"{contract.member_name}:row:{row_num}:{field}", "INVALID_EXPLICIT_TYPE", "Retain raw value and quarantine; do not coerce.")
        seen: set[tuple[str, ...]] = set()
        for offset, row in enumerate(rows, start=2):
            if contract.key_fields:
                absent = [field for field in contract.key_fields if field not in row or row[field] == ""]
                if absent:
                    add(f"{contract.member_name}:row:{offset}", "MISSING_DUPLICATE_KEY_COMPONENT", "Preserve row as unresolved and do not create an inferred key.")
                    continue
                key = tuple(row[field] for field in contract.key_fields)
                if key in seen:
                    add(f"{contract.member_name}:row:{offset}", "DUPLICATE_KEY", "Retain all source references and quarantine the ambiguous key group.")
                seen.add(key)
    except (csv.Error, StopIteration):
        add(contract.member_name, "CSV_PARSE_ERROR", "Reject member; preserve original bytes for review.")
        return ValidationReport("STRUCTURAL", "FAIL", tuple(findings)), ()
    status = "PASS" if not findings else "FAIL"
    return ValidationReport("STRUCTURAL", status, tuple(findings)), tuple(rows)
