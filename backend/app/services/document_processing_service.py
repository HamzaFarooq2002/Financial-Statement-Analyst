import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.agents.ai_insight_generator import generate_ai_insights
from app.agents.document_metadata_extractor import extract_document_metadata
from app.agents.financial_metric_extraction_agent import extract_financial_metrics
from app.core.config import settings
from app.models.document import Document, ProcessingStatus
from app.services.excel_report_generator import generate_excel_report
from app.services.pdf_parser import parse_pdf
from app.services.ratio_calculator import calculate_ratios


class DocumentProcessingError(Exception):
    """Raised when a document cannot be processed."""


RELEVANT_PAGE_KEYWORDS = [
    "total assets",
    "total liabilities",
    "total equity",
    "profit after tax",
    "net profit",
    "revenue",
    "markup income",
    "operating expenses",
    "earnings per share",
    "eps",
    "cash and balances",
    "advances",
    "loans",
    "deposits",
    "statement of financial position",
    "income statement",
    "profit and loss",
]


def process_document(document: Document, db: Session) -> dict[str, Any]:
    document.processing_status = ProcessingStatus.PROCESSING
    db.commit()

    artifacts_dir = _artifact_dir(document.id)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    try:
        parsed_text_only = parse_pdf(document.file_path, include_tables=False)
        relevant_pages = _select_relevant_pages(parsed_text_only)
        if not relevant_pages:
            raise DocumentProcessingError("No relevant financial statement pages were detected.")

        relevant_page_numbers = {page["page_number"] for page in relevant_pages}
        parsed_pdf = parse_pdf(document.file_path, table_page_numbers=relevant_page_numbers)
        _save_json(parsed_pdf, artifacts_dir / "parsed_pages.json")

        relevant_pages = _select_relevant_pages(parsed_pdf)
        if not relevant_pages:
            raise DocumentProcessingError("No relevant financial statement pages were detected.")

        if not settings.gemini_api_key:
            raise DocumentProcessingError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) is missing. Add it to backend/.env to extract "
                "metrics and generate insights."
            )

        metadata = extract_document_metadata(parsed_pdf)
        document.company_name = metadata.get("company_name")
        document.report_year = metadata.get("report_year")
        document.parent_document_id = _resolve_parent_document_id(
            db,
            company_name=document.company_name,
            report_year=document.report_year,
            exclude_document_id=document.id,
        )
        _save_json(metadata, artifacts_dir / "document_metadata.json")

        extracted_metrics = extract_financial_metrics(relevant_pages)
        _save_json(extracted_metrics, artifacts_dir / "extracted_metrics.json")

        calculated_ratios = calculate_ratios(extracted_metrics)
        _save_json(calculated_ratios, artifacts_dir / "calculated_ratios.json")

        ai_insights = generate_ai_insights(extracted_metrics, calculated_ratios)
        _save_json({"insights": ai_insights}, artifacts_dir / "ai_insights.json")

        excel_path = generate_excel_report(
            extracted_metrics=extracted_metrics,
            calculated_ratios=calculated_ratios,
            ai_insights=ai_insights,
            output_dir=artifacts_dir,
            filename=f"financial_report_{document.id}.xlsx",
        )

        dashboard = _build_dashboard(
            document=document,
            parsed_pdf=parsed_pdf,
            relevant_pages=relevant_pages,
            extracted_metrics=extracted_metrics,
            calculated_ratios=calculated_ratios,
            ai_insights=ai_insights,
            excel_path=excel_path,
        )
        _save_json(dashboard, artifacts_dir / "dashboard.json")

        document.processing_status = ProcessingStatus.COMPLETED
        db.commit()
        return dashboard
    except Exception as exc:
        document.processing_status = ProcessingStatus.FAILED
        db.commit()
        _save_json({"error": str(exc)}, artifacts_dir / "error.json")
        raise DocumentProcessingError(str(exc)) from exc


def fail_stale_processing_documents(db: Session) -> int:
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(
        seconds=settings.processing_timeout_seconds
    )
    stale_documents = (
        db.query(Document)
        .filter(Document.processing_status == ProcessingStatus.PROCESSING)
        .filter(Document.updated_at < cutoff)
        .all()
    )
    for document in stale_documents:
        document.processing_status = ProcessingStatus.FAILED
    if stale_documents:
        db.commit()
    return len(stale_documents)


def get_document_dashboard(document_id: int) -> dict[str, Any] | None:
    path = _artifact_dir(document_id) / "dashboard.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def get_document_excel_path(document_id: int) -> Path | None:
    path = _artifact_dir(document_id) / f"financial_report_{document_id}.xlsx"
    return path if path.exists() else None


def _artifact_dir(document_id: int) -> Path:
    return settings.export_dir / f"document_{document_id}"


def _normalize_company_key(name: str | None) -> str | None:
    if not name:
        return None
    key = " ".join(name.strip().lower().split())
    return key or None


def _resolve_parent_document_id(
    db: Session,
    *,
    company_name: str | None,
    report_year: int | None,
    exclude_document_id: int,
) -> int | None:
    """Link to the most recent prior-year completed document for the same company."""

    company_key = _normalize_company_key(company_name)
    if company_key is None or report_year is None:
        return None

    candidates = (
        db.query(Document)
        .filter(Document.id != exclude_document_id)
        .filter(Document.processing_status == ProcessingStatus.COMPLETED)
        .filter(Document.report_year.is_not(None))
        .filter(Document.report_year < report_year)
        .filter(Document.company_name.is_not(None))
        .all()
    )

    best_id: int | None = None
    best_year: int | None = None
    for other in candidates:
        if _normalize_company_key(other.company_name) != company_key:
            continue
        oy = other.report_year
        if oy is None:
            continue
        if best_year is None or oy > best_year:
            best_year = oy
            best_id = other.id
    return best_id


def _save_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _select_relevant_pages(parsed_pdf: dict[str, Any], limit: int = 12) -> list[dict[str, Any]]:
    scored_pages: list[tuple[int, dict[str, Any]]] = []
    for page in parsed_pdf.get("pages", []):
        text = str(page.get("text") or "")
        lower_text = text.lower()
        score = sum(1 for keyword in RELEVANT_PAGE_KEYWORDS if keyword in lower_text)
        if score or page.get("tables"):
            scored_pages.append((score, page))

    scored_pages.sort(key=lambda item: (item[0], len(str(item[1].get("text") or ""))), reverse=True)
    return [
        {
            "page_number": page["page_number"],
            "text": str(page.get("text") or "")[:12000],
            "tables": page.get("tables") or [],
        }
        for _, page in scored_pages[:limit]
    ]


def _build_dashboard(
    document: Document,
    parsed_pdf: dict[str, Any],
    relevant_pages: list[dict[str, Any]],
    extracted_metrics: dict[str, Any],
    calculated_ratios: dict[str, Any],
    ai_insights: list[dict[str, Any]],
    excel_path: str,
) -> dict[str, Any]:
    return {
        "document_id": document.id,
        "file_name": document.original_filename,
        "company_name": document.company_name,
        "report_year": document.report_year,
        "parent_document_id": document.parent_document_id,
        "processing_status": ProcessingStatus.COMPLETED.value,
        "page_count": len(parsed_pdf.get("pages", [])),
        "relevant_pages": [page["page_number"] for page in relevant_pages],
        "extracted_metrics": extracted_metrics,
        "calculated_ratios": calculated_ratios,
        "ai_insights": ai_insights,
        "source_references": _source_references(extracted_metrics),
        "excel_download_path": excel_path,
    }


def _source_references(extracted_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    references = []
    for metric in extracted_metrics.get("metrics", []):
        source_page = metric.get("source_page")
        if source_page is None:
            continue
        references.append(
            {
                "page": source_page,
                "label": metric.get("metric_name"),
                "snippet": metric.get("source_text"),
                "confidence_score": metric.get("confidence_score"),
            }
        )
    return references
