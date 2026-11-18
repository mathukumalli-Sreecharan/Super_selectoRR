"""Strict read-only loader for the project-owner-authorized competition archive."""

from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from pathlib import Path
from typing import Iterator


ARCHIVE_PATH = str(Path(__file__).resolve().parents[1] / "data" / "source" / "6af3166e7b922_data_pack.zip")
ARCHIVE_SIZE = 6143211
ARCHIVE_SHA256 = "a992ecd89b3f22c4d6bfdf5dc9faf767491f8199a6ec09c33ab347db675bd8e1"

MEMBER_IDS = {
    "6af855c0e8386_ball_by_ball.csv": (41071837, "01e2b4379edfbab6a6e456d304cb3c70f554cb312ef93d9588f3f32a82cb396e"),
    "matches.csv": (123864, "bb100ab84b8b9a15160c1f2315cf675210131a30e779ec5079fd5403dcf56eef"),
    "playing_eleven.csv": (966287, "7517c73722a28d5d61c808ccf0cbed315a8780586d02e946eb9a7f5daf011c27"),
    "competition_team_player_mapping.csv": (462969, "1ded4e42a933618572d6e2c3a521c3257eb1844fab4456d567d77cbb2d3bbb12"),
    "teams.csv": (6922, "a65e5922a9b3bf49247b24fc9471782e700efb31f8dcc5042923238b87c50a5d"),
    "competitions.csv": (7624, "507ceb7189f972d4e4f299ddcfc97f3c3247af1913f6291106f161fa8353fd9b"),
}


class SourceValidationError(ValueError):
    pass


def verify_member_metadata(archive_path: str = ARCHIVE_PATH) -> dict:
    """Verify archive/member metadata only. This function never opens CSV rows."""
    path = Path(archive_path)
    if not path.is_file():
        raise SourceValidationError("SOURCE_ARCHIVE_MISSING")
    if path.stat().st_size != ARCHIVE_SIZE:
        raise SourceValidationError("SOURCE_ARCHIVE_SIZE_MISMATCH")
    if hashlib.sha256(path.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise SourceValidationError("SOURCE_ARCHIVE_SHA256_MISMATCH")
    with zipfile.ZipFile(path, "r") as bundle:
        found = {info.filename: (info.file_size, hashlib.sha256(bundle.read(info)).hexdigest()) for info in bundle.infolist() if info.filename in MEMBER_IDS}
    for name, (size, digest) in MEMBER_IDS.items():
        actual = found.get(name)
        if actual is None or actual != (size, digest):
            raise SourceValidationError(f"SOURCE_MEMBER_MISMATCH:{name}")
    return {"archive_path": str(path), "archive_size": ARCHIVE_SIZE, "archive_sha256": ARCHIVE_SHA256, "members": MEMBER_IDS}


def iter_strict_csv_member(archive_path: str, member_name: str) -> Iterator[dict]:
    """Yield source rows after pinned archive/member integrity checks pass."""
    verify_member_metadata(archive_path)
    if member_name not in MEMBER_IDS:
        raise SourceValidationError("SOURCE_MEMBER_NOT_APPROVED")
    with zipfile.ZipFile(archive_path, "r") as bundle:
        matches = [info for info in bundle.infolist() if info.filename == member_name]
        if len(matches) != 1:
            raise SourceValidationError("SOURCE_MEMBER_DUPLICATE_OR_MISSING")
        payload = bundle.read(matches[0])
    text = io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8-sig", newline="")
    reader = csv.DictReader(text, strict=True)
    if not reader.fieldnames or any(not name for name in reader.fieldnames) or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise SourceValidationError("SOURCE_HEADER_INVALID")
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise SourceValidationError("SOURCE_ROW_WIDTH_MISMATCH")
        yield row
