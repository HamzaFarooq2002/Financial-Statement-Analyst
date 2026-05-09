from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings


@dataclass(frozen=True)
class SavedFile:
    original_filename: str
    stored_filename: str
    path: Path
    size_bytes: int


async def save_upload_file(file: UploadFile, upload_dir: Path) -> SavedFile:
    upload_dir.mkdir(parents=True, exist_ok=True)

    original_filename = Path(file.filename or "annual_report.pdf").name
    stored_filename = f"{uuid4().hex}.pdf"
    destination = upload_dir / stored_filename

    size_bytes = 0
    max_bytes = settings.max_upload_bytes

    with destination.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size_bytes += len(chunk)
            if size_bytes > max_bytes:
                output.close()
                destination.unlink(missing_ok=True)
                raise ValueError(f"Upload exceeds {settings.max_upload_mb} MB limit.")
            output.write(chunk)

    return SavedFile(
        original_filename=original_filename,
        stored_filename=stored_filename,
        path=destination,
        size_bytes=size_bytes,
    )

