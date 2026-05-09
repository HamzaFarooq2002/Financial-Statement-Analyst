"""Extract company name and fiscal/report year from early PDF pages via Gemini."""

from typing import Any

from google import genai
from pydantic import BaseModel, ConfigDict, Field

from app.agents.gemini_llm import GeminiGenerationError, create_gemini_client, generate_parsed
from app.core.config import settings


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str | None = Field(
        default=None,
        description="Legal or branding name of the reporting entity as shown on the cover/title.",
    )
    report_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Primary fiscal or reporting year (calendar year of the annual report).",
    )


def extract_document_metadata(
    parsed_pdf: dict[str, Any],
    *,
    client: genai.Client | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Return {'company_name': str|None, 'report_year': int|None} from the first pages."""

    pages = parsed_pdf.get("pages") or []
    preview_pages = pages[:3]
    if not preview_pages:
        return {"company_name": None, "report_year": None}

    chunks: list[str] = []
    for page in preview_pages:
        page_no = page.get("page_number", "?")
        text = str(page.get("text") or "").strip()[:8000]
        chunks.append(f"--- Page {page_no} ---\n{text}")

    user_text = "\n\n".join(chunks)
    system_instruction = (
        "You read the beginning of an annual or financial report PDF. "
        "Extract the reporting company's primary name (as printed on the cover or title page) "
        "and the main fiscal/reporting year for this document (e.g. 2023 for 'Annual Report 2023'). "
        "If unclear, use null for that field. Respond only as JSON matching the schema."
    )

    gemini_client = client or create_gemini_client()
    gemini_model = model or settings.gemini_model

    try:
        parsed = generate_parsed(
            gemini_client,
            gemini_model,
            system_instruction,
            user_text,
            DocumentMetadata,
            task_label="document metadata extraction",
        )
    except GeminiGenerationError:
        return {"company_name": None, "report_year": None}

    return {
        "company_name": parsed.company_name.strip() if parsed.company_name else None,
        "report_year": parsed.report_year,
    }
