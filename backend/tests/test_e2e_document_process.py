import io

import fitz


def _minimal_financial_pdf_bytes() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "CONSOLIDATED STATEMENT OF FINANCIAL POSITION\n"
        "Total assets 10,000 Total liabilities 8,000 Total equity 2,000\n"
        "INCOME STATEMENT\n"
        "Revenue or markup income 5,000 Operating expenses 1,200\n"
        "Profit after tax 400 Net profit after tax 400\n"
        "BASIC EPS 2.4\n"
        "Cash and balances with treasury 500\n"
        "Loans and advances to customers 3,000 Customer deposits 7,000\n"
    )
    page.insert_text((72, 72), text, fontsize=10)
    buf = doc.tobytes()
    doc.close()
    return buf


def test_upload_process_dashboard_excel_roundtrip_e2e(e2e_client):
    pdf_bytes = _minimal_financial_pdf_bytes()
    upload = e2e_client.post(
        "/api/documents/upload",
        files={"file": ("report.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload.status_code == 201, upload.text
    document_id = upload.json()["document_id"]

    process = e2e_client.post(f"/api/documents/{document_id}/process")
    assert process.status_code == 200, process.text
    body = process.json()
    assert body["processing_status"] == "completed"
    dashboard = body["dashboard"]
    assert dashboard["document_id"] == document_id
    assert dashboard["processing_status"] == "completed"
    assert len(dashboard["extracted_metrics"]["metrics"]) == 10
    assert len(dashboard["calculated_ratios"]["ratios"]) >= 10
    assert len(dashboard["ai_insights"]) == 5
    assert dashboard.get("company_name") == "Test Bank"
    assert dashboard.get("report_year") == 2024

    listing = e2e_client.get("/api/documents/")
    assert listing.status_code == 200
    listed = listing.json()
    assert len(listed) == 1
    assert listed[0]["document_id"] == document_id
    assert listed[0]["processing_status"] == "completed"

    related = e2e_client.get(f"/api/documents/{document_id}/related")
    assert related.status_code == 200
    assert related.json() == []

    dash_get = e2e_client.get(f"/api/documents/{document_id}/dashboard")
    assert dash_get.status_code == 200
    assert dash_get.json()["document_id"] == document_id

    xlsx = e2e_client.get(f"/api/documents/{document_id}/export/excel/download")
    assert xlsx.status_code == 200
    assert xlsx.headers.get("content-type", "").startswith(
        "application/vnd.openxmlformats-officedocument"
    )
    assert len(xlsx.content) > 2000
