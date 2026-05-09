from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.document import Document, ProcessingStatus
from app.schemas.document import (
    CompareDocumentsRequest,
    CompareDocumentsResponse,
    ComparisonDocumentMeta,
    DocumentProcessResponse,
    DocumentStatusResponse,
    DocumentSummaryResponse,
    DocumentUploadResponse,
)
from app.services.document_processing_service import (
    DocumentProcessingError,
    get_document_dashboard,
    get_document_excel_path,
    process_document,
)
from app.services.file_storage import save_upload_file
from app.services.multi_year_analyzer import run_comparison

router = APIRouter(prefix="/documents", tags=["documents"])


def _normalize_company_key(name: str | None) -> str | None:
    if not name:
        return None
    key = " ".join(name.strip().lower().split())
    return key or None


def _is_pdf(file: UploadFile) -> bool:
    filename = file.filename or ""
    content_type = file.content_type or ""
    return filename.lower().endswith(".pdf") or content_type == "application/pdf"


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    if not _is_pdf(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )

    saved_path: Path | None = None

    try:
        saved_file = await save_upload_file(file, settings.upload_dir)
        saved_path = saved_file.path

        document = Document(
            original_filename=saved_file.original_filename,
            stored_filename=saved_file.stored_filename,
            file_path=str(saved_file.path),
            content_type=file.content_type or "application/pdf",
            file_size_bytes=saved_file.size_bytes,
            processing_status=ProcessingStatus.UPLOADED,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        return DocumentUploadResponse(
            document_id=document.id,
            processing_status=document.processing_status.value,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store uploaded file.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        if saved_path and saved_path.exists():
            saved_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create document record.",
        ) from exc


@router.get("/", response_model=list[DocumentSummaryResponse])
def list_completed_documents(db: Session = Depends(get_db)) -> list[DocumentSummaryResponse]:
    documents = (
        db.query(Document)
        .filter(Document.processing_status == ProcessingStatus.COMPLETED)
        .order_by(Document.updated_at.desc())
        .all()
    )
    return [
        DocumentSummaryResponse(
            document_id=d.id,
            file_name=d.original_filename,
            processing_status=d.processing_status.value,
            company_name=d.company_name,
            report_year=d.report_year,
        )
        for d in documents
    ]


@router.post("/compare", response_model=CompareDocumentsResponse)
def compare_documents_route(
    payload: CompareDocumentsRequest,
    db: Session = Depends(get_db),
) -> CompareDocumentsResponse:
    try:
        data = run_comparison(db, payload.document_ids)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    documents = [ComparisonDocumentMeta.model_validate(d) for d in data["documents"]]
    return CompareDocumentsResponse(
        comparison_hash=data["comparison_hash"],
        documents=documents,
        metric_series=data["metric_series"],
        ratio_series=data["ratio_series"],
        trend_summary=data["trend_summary"],
        excel_download_path=data["excel_download_path"],
    )


@router.get("/compare/download/{comparison_hash}")
def download_comparison_excel(comparison_hash: str) -> FileResponse:
    key = comparison_hash.strip().lower()
    if len(key) != 16 or any(c not in "0123456789abcdef" for c in key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid comparison id.",
        )
    path = settings.export_dir / "comparisons" / f"comparison_{key}.xlsx"
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comparison Excel file not found. Run compare again.",
        )
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"comparison_{key}.xlsx",
    )


@router.get("/{document_id}/related", response_model=list[DocumentSummaryResponse])
def list_related_documents(document_id: int, db: Session = Depends(get_db)) -> list[DocumentSummaryResponse]:
    document = _get_document_or_404(document_id, db)
    company_key = _normalize_company_key(document.company_name)
    if not company_key:
        return []

    related = (
        db.query(Document)
        .filter(Document.id != document.id)
        .filter(Document.processing_status == ProcessingStatus.COMPLETED)
        .filter(Document.company_name.is_not(None))
        .order_by(Document.report_year.desc(), Document.id.desc())
        .all()
    )
    out: list[DocumentSummaryResponse] = []
    for item in related:
        if _normalize_company_key(item.company_name) == company_key:
            out.append(
                DocumentSummaryResponse(
                    document_id=item.id,
                    file_name=item.original_filename,
                    processing_status=item.processing_status.value,
                    company_name=item.company_name,
                    report_year=item.report_year,
                )
            )
    return out


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_status(
    document_id: int,
    db: Session = Depends(get_db),
) -> DocumentStatusResponse:
    document = _get_document_or_404(document_id, db)
    return DocumentStatusResponse(
        document_id=document.id,
        processing_status=document.processing_status.value,
        file_name=document.original_filename,
        company_name=document.company_name,
        report_year=document.report_year,
    )


@router.post("/{document_id}/process", response_model=DocumentProcessResponse)
def process_uploaded_document(
    document_id: int,
    db: Session = Depends(get_db),
) -> DocumentProcessResponse:
    document = _get_document_or_404(document_id, db)

    try:
        dashboard = process_document(document, db)
        return DocumentProcessResponse(
            document_id=document.id,
            processing_status=ProcessingStatus.COMPLETED.value,
            dashboard=dashboard,
        )
    except DocumentProcessingError as exc:
        return DocumentProcessResponse(
            document_id=document.id,
            processing_status=ProcessingStatus.FAILED.value,
            error=str(exc),
        )


@router.get("/{document_id}/dashboard")
def get_processed_dashboard(document_id: int, db: Session = Depends(get_db)) -> dict:
    document = _get_document_or_404(document_id, db)
    dashboard = get_document_dashboard(document.id)
    if dashboard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard is not available yet. Process the document first.",
        )
    return dashboard


@router.get("/{document_id}/export/excel/download")
def download_excel_report(document_id: int, db: Session = Depends(get_db)) -> FileResponse:
    document = _get_document_or_404(document_id, db)
    excel_path = get_document_excel_path(document.id)
    if excel_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Excel report is not available yet. Process the document first.",
        )
    return FileResponse(
        excel_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"financial_report_{document.id}.xlsx",
    )


def _get_document_or_404(document_id: int, db: Session) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return document
