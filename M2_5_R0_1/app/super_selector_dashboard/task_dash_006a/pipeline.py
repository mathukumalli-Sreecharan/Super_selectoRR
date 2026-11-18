"""Synthetic-only in-memory validation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Mapping

_V015_ROOT = Path(__file__).resolve().parents[1] / "versions" / "TASK_DASH_002_implementation_v0_1_5"
if str(_V015_ROOT) not in sys.path:
    sys.path.insert(0, str(_V015_ROOT))
from services.authorization import PRODUCTION_GATE  # noqa: E402

from .archive import ArchiveManifest, VerifiedArchive, verify_archive_bytes
from .contracts import CsvSchemaContract
from .reporting import ValidationFinding, ValidationReport
from .structural import validate_csv_bytes


@dataclass(frozen=True)
class SyntheticArchive:
    label: str
    payload: bytes
    manifest: ArchiveManifest
    schemas: Mapping[str, CsvSchemaContract]
    evidence_ref: str


@dataclass(frozen=True)
class ValidationRun:
    archive: VerifiedArchive | None
    archive_report: ValidationReport
    structural_reports: tuple[ValidationReport, ...]
    data_mode: str = "SYNTHETIC"

    @property
    def status(self) -> str:
        reports = (self.archive_report,) + self.structural_reports
        return "FAIL" if any(report.status == "FAIL" for report in reports) else "PASS"


def validate_synthetic_archive(fixture: SyntheticArchive, *, mode: str = "SYNTHETIC") -> ValidationRun:
    """Validate only explicitly labelled in-memory fixtures; no path loader."""
    if mode != "SYNTHETIC":
        PRODUCTION_GATE.require_production_authorization("read or validate a production source archive")
    if not isinstance(fixture, SyntheticArchive) or fixture.label != "SYNTHETIC":
        raise ValueError("Only explicitly labelled SYNTHETIC fixtures are accepted.")
    try:
        archive = verify_archive_bytes(fixture.payload, fixture.manifest)
    except (ValueError, OSError) as exc:
        code = str(exc).split(":", 1)[0]
        finding = ValidationFinding(
            "ARCHIVE", "SYNTHETIC:archive", "FAIL", code, fixture.evidence_ref, "",
            "Reject archive; preserve fixture bytes and reason code.",
        )
        return ValidationRun(None, ValidationReport("ARCHIVE", "FAIL", (finding,)), ())
    archive_report = ValidationReport(
        "ARCHIVE", "PASS", (
            ValidationFinding("ARCHIVE", "SYNTHETIC:archive", "PASS", "ARCHIVE_AND_MEMBERS_VERIFIED", fixture.evidence_ref, "", "Proceed to structural checks."),
        ),
    )
    reports = []
    for member_name, schema in fixture.schemas.items():
        payload = archive.member_payloads.get(member_name)
        if payload is None:
            raise ValueError(f"Schema refers to absent verified member: {member_name}")
        report, _rows = validate_csv_bytes(payload, schema, evidence_ref=fixture.evidence_ref)
        reports.append(report)
    return ValidationRun(archive, archive_report, tuple(reports))
