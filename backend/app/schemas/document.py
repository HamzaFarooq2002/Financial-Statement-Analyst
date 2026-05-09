from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadResponse(BaseModel):
    document_id: int
    processing_status: str

    model_config = ConfigDict(from_attributes=True)


class DocumentStatusResponse(BaseModel):
    document_id: int
    processing_status: str
    file_name: str
    company_name: str | None = None
    report_year: int | None = None


class DocumentSummaryResponse(BaseModel):
    document_id: int
    file_name: str
    processing_status: str
    company_name: str | None = None
    report_year: int | None = None


class CompareDocumentsRequest(BaseModel):
    document_ids: list[int] = Field(min_length=2)


class ComparisonDocumentMeta(BaseModel):
    document_id: int
    file_name: str
    company_name: str | None = None
    report_year: int | None = None


class CompareDocumentsResponse(BaseModel):
    comparison_hash: str
    documents: list[ComparisonDocumentMeta]
    metric_series: list[dict[str, Any]]
    ratio_series: list[dict[str, Any]]
    trend_summary: dict[str, Any]
    excel_download_path: str


class DocumentProcessResponse(BaseModel):
    document_id: int
    processing_status: str
    dashboard: dict | None = None
    error: str | None = None
