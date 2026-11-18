"""In-memory archive verification primitives for synthetic fixtures only."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
from collections.abc import Mapping
import zipfile


class ArchiveValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ExpectedMember:
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class ArchiveManifest:
    archive_sha256: str
    members: Mapping[str, ExpectedMember]


@dataclass(frozen=True)
class VerifiedArchive:
    archive_sha256: str
    member_payloads: Mapping[str, bytes]
    status: str = "PASS"
    data_mode: str = "SYNTHETIC"


def verify_archive_bytes(payload: bytes, manifest: ArchiveManifest) -> VerifiedArchive:
    """Verify archive/member identity without opening a path or reading files.

    Callers must supply bytes already designated synthetic. There is no
    filesystem/archive-path loader in this package.
    """
    if not isinstance(payload, bytes):
        raise ArchiveValidationError("Synthetic archive payload must be bytes.")
    if not isinstance(manifest, ArchiveManifest):
        raise ArchiveValidationError("An explicit ArchiveManifest is required.")
    if not isinstance(manifest.members, Mapping):
        raise ArchiveValidationError("INVALID_EXPECTED_MEMBER_CONTRACT")
    if not isinstance(manifest.archive_sha256, str) or len(manifest.archive_sha256) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in manifest.archive_sha256):
        raise ArchiveValidationError("INVALID_EXPECTED_ARCHIVE_SHA256")
    for name, expected in manifest.members.items():
        if not isinstance(name, str) or not name or not isinstance(expected, ExpectedMember):
            raise ArchiveValidationError("INVALID_EXPECTED_MEMBER_CONTRACT")
        if type(expected.size_bytes) is not int or expected.size_bytes < 0:
            raise ArchiveValidationError("INVALID_EXPECTED_MEMBER_SIZE:" + name)
        if not isinstance(expected.sha256, str) or len(expected.sha256) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in expected.sha256):
            raise ArchiveValidationError("INVALID_EXPECTED_MEMBER_SHA256:" + name)
    actual_archive_hash = hashlib.sha256(payload).hexdigest()
    if actual_archive_hash != manifest.archive_sha256.lower():
        raise ArchiveValidationError("ARCHIVE_SHA256_MISMATCH")
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload), "r")
    except (zipfile.BadZipFile, OSError) as exc:
        raise ArchiveValidationError("INVALID_ZIP_ARCHIVE") from exc
    with archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise ArchiveValidationError("DUPLICATE_ARCHIVE_MEMBER")
        expected = set(manifest.members)
        found = set(names)
        missing, extra = expected - found, found - expected
        if missing:
            raise ArchiveValidationError("MISSING_ARCHIVE_MEMBER:" + ";".join(sorted(missing)))
        if extra:
            raise ArchiveValidationError("UNEXPECTED_ARCHIVE_MEMBER:" + ";".join(sorted(extra)))
        if archive.testzip() is not None:
            raise ArchiveValidationError("ZIP_MEMBER_CRC_FAILURE")
        payloads: dict[str, bytes] = {}
        for info in infos:
            if info.is_dir():
                raise ArchiveValidationError("UNEXPECTED_DIRECTORY_MEMBER:" + info.filename)
            content = archive.read(info)
            contract = manifest.members[info.filename]
            if info.file_size != contract.size_bytes:
                raise ArchiveValidationError("MEMBER_SIZE_MISMATCH:" + info.filename)
            digest = hashlib.sha256(content).hexdigest()
            if digest != contract.sha256.lower():
                raise ArchiveValidationError("MEMBER_SHA256_MISMATCH:" + info.filename)
            payloads[info.filename] = content
    return VerifiedArchive(actual_archive_hash, payloads)
