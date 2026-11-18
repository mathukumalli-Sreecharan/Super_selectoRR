"""Shared result types for synthetic and, after separate authorization, source checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Iterable, Mapping


STATUSES = {"PASS", "PASS WITH LIMITATIONS", "FAIL", "NOT VALIDATED"}


@dataclass(frozen=True)
class ValidationException:
    validation_id: str
    exception_code: str
    severity: str
    match_id: str | None = None
    innings_id: str | None = None
    over_id: str | None = None
    delivery_id: str | None = None
    player_id: str | None = None
    field_name: str | None = None
    expected_rule: str | None = None
    disposition: str = "Review source evidence; no value inferred."


@dataclass(frozen=True)
class ValidationResult:
    validation_id: str
    status: str
    records_examined: int
    records_passed: int
    exception_count: int
    limitation_count: int
    metrics: Mapping[str, int | float | str | None] = field(default_factory=dict)
    exceptions: tuple[ValidationException, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"Unsupported validation status: {self.status}")

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["exceptions"] = [asdict(item) for item in self.exceptions]
        return result


def result(
    validation_id: str,
    rows: Iterable[Mapping[str, Any]],
    exceptions: list[ValidationException],
    *,
    metrics: Mapping[str, int | float | str | None] | None = None,
    limitations: int = 0,
    records_passed: int | None = None,
) -> ValidationResult:
    count = len(rows) if hasattr(rows, "__len__") else sum(1 for _ in rows)
    if any(x.severity == "ERROR" for x in exceptions):
        status = "FAIL"
    elif count == 0 or any(x.severity == "UNRESOLVED" for x in exceptions):
        status = "NOT VALIDATED"
    elif limitations or any(x.severity == "LIMITATION" for x in exceptions):
        status = "PASS WITH LIMITATIONS"
    else:
        status = "PASS"
    return ValidationResult(
        validation_id=validation_id,
        status=status,
        records_examined=count,
        records_passed=(records_passed if records_passed is not None else max(0, count - len(exceptions))),
        exception_count=len(exceptions),
        limitation_count=limitations + sum(x.severity == "LIMITATION" for x in exceptions),
        metrics=metrics or {},
        exceptions=tuple(exceptions),
    )


def identifier(row: Mapping[str, Any], key: str) -> str | None:
    value = row.get(key)
    if value is None or value == "":
        return None
    return str(value)


def nonnegative_int(value: Any) -> bool:
    parsed = integer_value(value)
    return parsed is not None and parsed >= 0


def positive_int(value: Any) -> bool:
    parsed = integer_value(value)
    return parsed is not None and parsed > 0


def integer_value(value: Any) -> int | None:
    """Parse an integer field without treating blank/malformed values as zero."""
    if type(value) is int:
        return value
    if isinstance(value, str) and re.fullmatch(r"-?[0-9]+", value):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def row_exception(
    validation_id: str,
    code: str,
    severity: str,
    row: Mapping[str, Any],
    *,
    field_name: str | None = None,
    expected_rule: str | None = None,
) -> ValidationException:
    return ValidationException(
        validation_id=validation_id,
        exception_code=code,
        severity=severity,
        match_id=identifier(row, "match_id"),
        innings_id=identifier(row, "innings_id"),
        over_id=identifier(row, "overid"),
        delivery_id=identifier(row, "delivery_id"),
        player_id=identifier(row, "player_id"),
        field_name=field_name,
        expected_rule=expected_rule,
    )
