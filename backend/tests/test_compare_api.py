"""Route-level checks for document listing and compare (mocked engine work)."""

import pytest


def test_compare_documents_requires_two_ids(e2e_client):
    res = e2e_client.post("/api/documents/compare", json={"document_ids": [1]})
    assert res.status_code == 422


def test_compare_documents_returns_payload(monkeypatch, e2e_client):
    payload = {
        "comparison_hash": "0123456789abcdef",
        "documents": [
            {"document_id": 1, "file_name": "a.pdf", "company_name": "Co", "report_year": 2022},
            {"document_id": 2, "file_name": "b.pdf", "company_name": "Co", "report_year": 2023},
        ],
        "metric_series": [
            {"metric_name": "total_assets", "unit": "USD", "points": [{"document_id": 1, "report_year": 2022, "value": 1}]},
        ],
        "ratio_series": [],
        "trend_summary": {"headline": "Hi", "bullets": ["a", "b", "c"], "confidence": 0.9},
        "excel_download_path": "/nonexistent/path.xlsx",
    }

    def _fake_run_comparison(db, document_ids):  # noqa: ARG001
        assert sorted(document_ids) == [1, 2]
        return payload

    monkeypatch.setattr(
        "app.api.routes.uploads.run_comparison",
        _fake_run_comparison,
    )

    res = e2e_client.post("/api/documents/compare", json={"document_ids": [2, 1]})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["comparison_hash"] == payload["comparison_hash"]
    assert len(body["documents"]) == 2


def test_list_completed_documents_empty(e2e_client):
    res = e2e_client.get("/api/documents/")
    assert res.status_code == 200
    assert res.json() == []


def test_compare_download_rejects_invalid_hash(e2e_client):
    res = e2e_client.get("/api/documents/compare/download/not-valid-hex-chars")
    assert res.status_code == 400
