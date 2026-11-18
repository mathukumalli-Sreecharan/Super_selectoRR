"""Structured, mode-labelled validation evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
from io import StringIO


FINDING_FIELDS = (
    "category", "record_ref", "status", "reason_code", "evidence_ref",
    "affected_scenarios", "recommended_disposition", "data_mode",
)


@dataclass(frozen=True)
class ValidationFinding:
    category: str
    record_ref: str
    status: str
    reason_code: str
    evidence_ref: str
    affected_scenarios: str
    recommended_disposition: str
    data_mode: str = "SYNTHETIC"

    def as_row(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationReport:
    category: str
    status: str
    findings: tuple[ValidationFinding, ...]
    data_mode: str = "SYNTHETIC"

    def __post_init__(self) -> None:
        if self.data_mode != "SYNTHETIC":
            raise ValueError("This package only emits SYNTHETIC validation reports.")


def findings_csv(reports: tuple[ValidationReport, ...]) -> str:
    """Serialize findings in the documented, stable validation-output schema."""
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FINDING_FIELDS, lineterminator="\n")
    writer.writeheader()
    for report in reports:
        if report.data_mode != "SYNTHETIC":
            raise ValueError("Production validation output is not supported.")
        if report.findings:
            for finding in report.findings:
                writer.writerow(finding.as_row())
        else:
            writer.writerow({
                "category": report.category,
                "record_ref": "SYNTHETIC:report",
                "status": report.status,
                "reason_code": "VALIDATION_PASSED",
                "evidence_ref": "SYNTHETIC:report",
                "affected_scenarios": "",
                "recommended_disposition": "No issues found under the supplied synthetic contract.",
                "data_mode": "SYNTHETIC",
            })
    return output.getvalue()
