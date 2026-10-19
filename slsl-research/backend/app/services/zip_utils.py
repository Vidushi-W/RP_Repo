"""Safe ZIP extraction utilities."""

import zipfile
from pathlib import Path


def safe_extract_zip(zip_path: Path, dest_dir: Path) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    dest_resolved = dest_dir.resolve()
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Unsafe path in ZIP archive: {member.filename}")
            target = (dest_dir / member.filename).resolve()
            if not str(target).startswith(str(dest_resolved)):
                raise ValueError(f"ZIP path traversal blocked: {member.filename}")
            zf.extract(member, dest_dir)
            if not member.is_dir():
                extracted.append(target)
    return extracted
