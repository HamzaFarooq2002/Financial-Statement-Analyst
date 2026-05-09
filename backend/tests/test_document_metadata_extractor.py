"""document_metadata_extractor does not call Gemini when preview pages are empty."""

from app.agents.document_metadata_extractor import extract_document_metadata


def test_extract_document_metadata_returns_none_when_no_pages():
    result = extract_document_metadata({"pages": []})
    assert result == {"company_name": None, "report_year": None}


def test_extract_document_metadata_returns_none_when_pages_missing():
    result = extract_document_metadata({})
    assert result == {"company_name": None, "report_year": None}
