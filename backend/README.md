# AI Financial Report Analyst Backend

FastAPI scaffold for uploading annual report PDFs and storing document records in SQLite.

## Setup

Always run the API **from this `backend` folder** so Python can import the `app` package.

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

From the repo root you can use `.\scripts\dev-backend.ps1` (or `scripts\dev-backend.bat`) instead; it `cd`s here automatically.

## Endpoints

- `GET /health`
- `POST /api/documents/upload`
- `GET /api/documents/` — list completed documents (`company_name`, `report_year`, …)
- `GET /api/documents/{id}/related` — same-company completed reports for comparison
- `POST /api/documents/compare` — JSON `{ "document_ids": [int, …] }` for multi-year analysis + Excel
- `GET /api/documents/compare/download/{comparison_hash}` — comparison workbook download

The upload endpoint accepts a multipart field named `file` and returns:

```json
{
  "document_id": 1,
  "processing_status": "uploaded"
}
```
