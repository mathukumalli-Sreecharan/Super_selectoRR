"""Read-only archive adapter; gate is checked before archive/member access."""

from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from pathlib import Path
from typing import Any, Iterator, Mapping

from .authorization import authorize_stage2


class SourceIntegrityError(ValueError):
    pass


def iter_authorized_csv_rows(
    *,
    authorization_record: Mapping[str, Any] | None,
    archive_path: str | Path,
    expected_archive_size: int,
    expected_archive_sha256: str,
    member_name: str,
    expected_member_size: int,
    expected_member_sha256: str,
) -> Iterator[dict[str, str]]:
    """Yield rows only after a complete, trusted Stage 2 grant is verifiable."""
    authorize_stage2(authorization_record)
    if "source_row_read_only" not in authorization_record.get("permitted_operations", []):
        raise SourceIntegrityError("READ_ONLY_SOURCE_ACCESS_NOT_AUTHORIZED")
    if Path(authorization_record["output_contract"]["directory"]).exists():
        raise SourceIntegrityError("AUTHORIZED_OUTPUT_DIRECTORY_ALREADY_EXISTS")
    if expected_archive_size > authorization_record["execution_environment"]["max_input_bytes"]:
        raise SourceIntegrityError("AUTHORIZED_INPUT_SIZE_LIMIT_EXCEEDED")
    approved_source = authorization_record["source"]
    if (
        str(archive_path) != approved_source.get("archive_path")
        or expected_archive_size != approved_source.get("archive_size_bytes")
        or expected_archive_sha256 != approved_source.get("archive_sha256")
    ):
        raise SourceIntegrityError("SOURCE_ARCHIVE_NOT_BOUND_TO_AUTHORIZATION")
    approved_members = approved_source.get("members")
    if not isinstance(approved_members, list):
        raise SourceIntegrityError("AUTHORIZED_MEMBER_LIST_INVALID")
    member_bindings = [item for item in approved_members if isinstance(item, Mapping) and item.get("name") == member_name]
    if len(member_bindings) != 1 or (
        member_bindings[0].get("size_bytes") != expected_member_size
        or member_bindings[0].get("sha256") != expected_member_sha256
    ):
        raise SourceIntegrityError("SOURCE_MEMBER_NOT_BOUND_TO_AUTHORIZATION")
    # The current hard gate raises above; these statements are prepared for a
    # later separately approved release and were not executed for this task.
    archive = Path(archive_path)
    if archive.stat().st_size != expected_archive_size:
        raise SourceIntegrityError("SOURCE_ARCHIVE_SIZE_MISMATCH")
    archive_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if archive_digest != expected_archive_sha256:
        raise SourceIntegrityError("SOURCE_ARCHIVE_SHA256_MISMATCH")
    with zipfile.ZipFile(archive, "r") as bundle:
        infos = [item for item in bundle.infolist() if item.filename == member_name]
        if len(infos) != 1 or infos[0].file_size != expected_member_size:
            raise SourceIntegrityError("SOURCE_MEMBER_IDENTITY_MISMATCH")
        if infos[0].file_size > authorization_record["execution_environment"]["max_input_bytes"]:
            raise SourceIntegrityError("AUTHORIZED_MEMBER_SIZE_LIMIT_EXCEEDED")
        payload = bundle.read(infos[0])
    if hashlib.sha256(payload).hexdigest() != expected_member_sha256:
        raise SourceIntegrityError("SOURCE_MEMBER_SHA256_MISMATCH")
    text = io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8-sig", newline="")
    reader = csv.DictReader(text, strict=True)
    if not reader.fieldnames or any(not name for name in reader.fieldnames) or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise SourceIntegrityError("SOURCE_HEADER_MISSING_DUPLICATE_OR_BLANK")
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise SourceIntegrityError("SOURCE_ROW_WIDTH_MISMATCH")
        yield row
