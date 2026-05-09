from pathlib import Path
from typing import Any

import pdfplumber
import pymupdf


class PDFParserError(Exception):
    """Base exception for PDF parser failures."""


class PDFNotFoundError(PDFParserError):
    """Raised when the requested PDF path is missing."""


class PDFParseError(PDFParserError):
    """Raised when text or table extraction fails."""


ExtractedPDF = dict[str, list[dict[str, Any]]]


def parse_pdf(
    pdf_path: str | Path,
    *,
    include_tables: bool = True,
    table_page_numbers: set[int] | None = None,
) -> ExtractedPDF:
    path = Path(pdf_path)
    _validate_pdf_path(path)

    try:
        pages = _extract_page_text(path)
        tables_by_page = (
            _extract_page_tables(path, page_numbers=table_page_numbers) if include_tables else {}
        )
    except PDFParserError:
        raise
    except Exception as exc:
        raise PDFParseError(f"Failed to parse PDF: {path}") from exc

    for page in pages:
        page["tables"] = tables_by_page.get(page["page_number"], [])

    return {"pages": pages}


def _validate_pdf_path(path: Path) -> None:
    if not path.exists():
        raise PDFNotFoundError(f"PDF file does not exist: {path}")
    if not path.is_file():
        raise PDFNotFoundError(f"PDF path is not a file: {path}")
    if path.suffix.lower() != ".pdf":
        raise PDFParseError(f"Expected a PDF file, received: {path.name}")


def _extract_page_text(path: Path) -> list[dict[str, Any]]:
    try:
        with pymupdf.open(path) as document:
            if document.is_encrypted:
                raise PDFParseError("Encrypted PDFs are not supported.")

            return [
                {
                    "page_number": page_index + 1,
                    "text": page.get_text("text").strip(),
                    "tables": [],
                }
                for page_index, page in enumerate(document)
            ]
    except PDFParseError:
        raise
    except Exception as exc:
        raise PDFParseError(f"Failed to extract text from PDF: {path}") from exc


def _extract_page_tables(
    path: Path,
    page_numbers: set[int] | None = None,
) -> dict[int, list[list[list[str | None]]]]:
    try:
        with pdfplumber.open(path) as document:
            tables_by_page = {}
            for page_index, page in enumerate(document.pages):
                page_number = page_index + 1
                if page_numbers is not None and page_number not in page_numbers:
                    continue
                tables_by_page[page_number] = page.extract_tables() or []
            return tables_by_page
    except Exception as exc:
        raise PDFParseError(f"Failed to extract tables from PDF: {path}") from exc
