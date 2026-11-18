"""CSV and minimal PDF exports; no ranking formula or real ranking is selected."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Mapping


def export_csv(path: str | Path, rows: Iterable[Mapping], fieldnames: list[str]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def export_pdf(path: str | Path, title: str, sections: list[tuple[str, str]]) -> None:
    """Generate a small standards-compatible text PDF without third-party packages."""
    lines = [title]
    for heading, body in sections:
        lines.extend([heading, body])
    safe = []
    for line in lines:
        safe.append(str(line).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                      .encode("ascii", "replace").decode("ascii"))
    stream_lines = ["BT", "/F1 10 Tf", "72 750 Td"]
    for line in safe[:80]:
        stream_lines.append(f"({line[:180]}) Tj")
        stream_lines.append("0 -14 Td")
    stream_lines.append("ET")
    content = "\n".join(stream_lines).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects)+1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(pdf)
